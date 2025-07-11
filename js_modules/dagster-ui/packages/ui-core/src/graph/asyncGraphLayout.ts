import memoize from 'lodash/memoize';
import {useEffect, useLayoutEffect, useMemo, useReducer, useRef} from 'react';
import {Worker} from 'shared/workers/Worker.oss';

import {ILayoutOp, LayoutOpGraphOptions, OpGraphLayout, layoutOpGraph} from './layout';
import {useFeatureFlags} from '../app/Flags';
import {asyncMemoize, indexedDBAsyncMemoize} from '../app/Util';
import {GraphData} from '../asset-graph/Utils';
import {AssetGraphLayout, LayoutAssetGraphOptions, layoutAssetGraph} from '../asset-graph/layout';
import {useDangerousRenderEffect} from '../hooks/useDangerousRenderEffect';
import {useBlockTraceUntilTrue} from '../performance/TraceContext';
import {hashObject} from '../util/hashObject';
import {weakMapMemoize} from '../util/weakMapMemoize';
import {workerSpawner} from '../workers/workerSpawner';

const ASYNC_LAYOUT_SOLID_COUNT = 50;

// If you're working on the layout logic, set to false so hot-reloading re-computes the layout
const CACHING_ENABLED = true;

// Op Graph

const _opLayoutCacheKey = (ops: ILayoutOp[], opts: LayoutOpGraphOptions) => {
  const solidKey = ops.map((x) => x.name).join('|');
  const parentKey = opts.parentOp?.name;
  return `${solidKey}:${parentKey}`;
};

export const getFullOpLayout = memoize(layoutOpGraph, _opLayoutCacheKey);

const asyncGetFullOpLayout = asyncMemoize((ops: ILayoutOp[], opts: LayoutOpGraphOptions) => {
  return new Promise<OpGraphLayout>((resolve) => {
    const worker = spawnLayoutWorker();
    worker.onMessage((event) => {
      resolve(event.data);
      worker.terminate();
    });
    worker.postMessage({type: 'layoutOpGraph', ops, opts});
  });
}, _opLayoutCacheKey);

const _assetLayoutCacheKey = weakMapMemoize(
  (graphData: GraphData, opts: LayoutAssetGraphOptions) => {
    return hashObject({
      opts,
      graphData,
      version: 5,
    });
  },
);

const getFullAssetLayout = memoize(layoutAssetGraph, _assetLayoutCacheKey);

const EMPTY_LAYOUT: AssetGraphLayout = {
  width: 0,
  height: 0,
  nodes: {},
  edges: [],
  groups: {},
};

export const asyncGetFullAssetLayoutIndexDB = indexedDBAsyncMemoize(
  (graphData: GraphData, opts: LayoutAssetGraphOptions) => {
    return new Promise<AssetGraphLayout>((resolve) => {
      const worker = spawnLayoutWorker();
      worker.onMessage((event) => {
        resolve(event.data);
        worker.terminate();
      });
      worker.onError((error) => {
        console.error(error);
        resolve(EMPTY_LAYOUT);
      });
      worker.postMessage({type: 'layoutAssetGraph', opts, graphData});
    });
  },
  'asyncGetFullAssetLayoutIndexDB',
  _assetLayoutCacheKey,
);

const asyncGetFullAssetLayout = asyncMemoize(
  (graphData: GraphData, opts: LayoutAssetGraphOptions) => {
    return new Promise<AssetGraphLayout>((resolve) => {
      const worker = spawnLayoutWorker();
      worker.onMessage((event) => {
        resolve(event.data);
        worker.terminate();
      });
      worker.onError((error) => {
        console.error(error);
        resolve(EMPTY_LAYOUT);
      });
      worker.postMessage({type: 'layoutAssetGraph', opts, graphData});
    });
  },
  _assetLayoutCacheKey,
);

const spawnLayoutWorker = workerSpawner(
  () => new Worker(new URL('../workers/dagre_layout.worker', import.meta.url)),
);
// Helper Hooks:
// - Automatically switch between sync and async loading strategies
// - Re-layout when the cache key function returns a different value

type State = {
  loading: boolean;
  layout: OpGraphLayout | AssetGraphLayout | null;
  cacheKey: string;
};

type Action =
  | {type: 'loading'}
  | {
      type: 'layout';
      payload: {
        layout: OpGraphLayout | AssetGraphLayout;
        cacheKey: string;
      };
    };

const reducer = (state: State, action: Action): State => {
  switch (action.type) {
    case 'loading':
      return {loading: true, layout: state.layout, cacheKey: state.cacheKey};
    case 'layout':
      return {
        loading: false,
        layout: action.payload.layout,
        cacheKey: action.payload.cacheKey,
      };
    default:
      return state;
  }
};

const initialState: State = {
  loading: false,
  layout: null,
  cacheKey: '',
};

/**
 * Todo: It would be nice to merge these hooks into one, passing the sync + async layout methods in as args.
 * I tried but felt like the complexity wasn't worth the code savings. The key problem is that the layout
 * functions take different args and a generic solution loses the types.
 */

export function useOpLayout(ops: ILayoutOp[], parentOp?: ILayoutOp) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const cacheKey = _opLayoutCacheKey(ops, {parentOp});
  const runAsync = ops.length >= ASYNC_LAYOUT_SOLID_COUNT;

  useEffect(() => {
    async function runAsyncLayout() {
      dispatch({type: 'loading'});
      const layout = await asyncGetFullOpLayout(ops, {parentOp});
      dispatch({
        type: 'layout',
        payload: {layout, cacheKey},
      });
    }

    if (!runAsync || typeof window.Worker === 'undefined') {
      const layout = getFullOpLayout(ops, {parentOp});
      dispatch({type: 'layout', payload: {layout, cacheKey}});
    } else {
      void runAsyncLayout();
    }
  }, [cacheKey, ops, parentOp, runAsync]);

  const uid = useRef(0);
  useDangerousRenderEffect(() => {
    uid.current++;
  }, [cacheKey, ops, parentOp, runAsync]);

  const loading = state.loading || !state.layout || state.cacheKey !== cacheKey;

  // Add a UID to create a new dependency whenever the layout inputs change
  useBlockTraceUntilTrue('useAssetLayout', !loading && !!state.layout, {
    uid: uid.current.toString(),
  });

  return {
    loading: state.loading || !state.layout || state.cacheKey !== cacheKey,
    async: runAsync,
    layout: state.layout as OpGraphLayout | null,
  };
}

export function useAssetLayout(
  _graphData: GraphData,
  expandedGroups: string[],
  opts: LayoutAssetGraphOptions,
  dataLoading?: boolean,
) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const flags = useFeatureFlags();

  const graphData = useMemo(() => ({..._graphData, expandedGroups}), [expandedGroups, _graphData]);

  const cacheKey = useMemo(() => _assetLayoutCacheKey(graphData, opts), [graphData, opts]);
  const nodeCount = Object.keys(graphData.nodes).length;
  const runAsync = nodeCount >= ASYNC_LAYOUT_SOLID_COUNT;

  useLayoutEffect(() => {
    if (dataLoading) {
      return;
    }
    let canceled = false;
    async function runAsyncLayout() {
      dispatch({type: 'loading'});
      let layout;
      if (CACHING_ENABLED) {
        layout = await asyncGetFullAssetLayoutIndexDB(graphData, opts);
      } else {
        layout = await asyncGetFullAssetLayout(graphData, opts);
      }
      if (canceled) {
        return;
      }
      dispatch({type: 'layout', payload: {layout, cacheKey}});
    }

    if (!runAsync) {
      const layout = getFullAssetLayout(graphData, opts);
      dispatch({type: 'layout', payload: {layout, cacheKey}});
    } else {
      void runAsyncLayout();
    }

    return () => {
      canceled = true;
    };
  }, [cacheKey, graphData, runAsync, flags, opts, dataLoading]);

  const uid = useRef(0);
  useDangerousRenderEffect(() => {
    uid.current++;
  }, [cacheKey, graphData, runAsync, flags, opts]);

  const loading = state.loading || !state.layout || state.cacheKey !== cacheKey;

  // Add a UID to create a new dependency whenever the layout inputs change
  useBlockTraceUntilTrue('useAssetLayout', !loading && !!state.layout, {
    uid: uid.current.toString(),
  });

  return {
    loading,
    async: runAsync,
    layout: state.layout as AssetGraphLayout | null,
  };
}

export {layoutOp} from './layout';
export type {OpGraphLayout, OpLayout, OpLayoutEdge} from './layout';
