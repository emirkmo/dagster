// Same as PartitionRangeStatus but we need a "MISSING" value

import {Colors} from '@dagster-io/ui';
import {CSSProperties} from 'react';

import {assertUnreachable} from '../app/Util';

// Same as PartitionRangeStatus but we need a "MISSING" value
//
export enum AssetPartitionStatus {
  FAILED = 'FAILED',
  MATERIALIZED = 'MATERIALIZED',
  MATERIALIZING = 'MATERIALIZING',
  MISSING = 'MISSING',
}

export const emptyAssetPartitionStatusCounts = () => ({
  [AssetPartitionStatus.MISSING]: 0,
  [AssetPartitionStatus.MATERIALIZED]: 0,
  [AssetPartitionStatus.MATERIALIZING]: 0,
  [AssetPartitionStatus.FAILED]: 0,
});

export const assetPartitionStatusToText = (status: AssetPartitionStatus) => {
  switch (status) {
    case AssetPartitionStatus.MATERIALIZED:
      return 'Materialized';
    case AssetPartitionStatus.MATERIALIZING:
      return 'Materializing';
    case AssetPartitionStatus.FAILED:
      return 'Failed';
    case AssetPartitionStatus.MISSING:
      return 'Missing';
    default:
      assertUnreachable(status);
  }
};

export const assetPartitionStatusToColor = (status: AssetPartitionStatus) => {
  switch (status) {
    case AssetPartitionStatus.MATERIALIZED:
      return Colors.Green500;
    case AssetPartitionStatus.MATERIALIZING:
      return Colors.Blue500;
    case AssetPartitionStatus.FAILED:
      return Colors.Red500;
    case AssetPartitionStatus.MISSING:
      return Colors.Gray200;
    default:
      assertUnreachable(status);
  }
};

export const assetPartitionStatusesToStyle = (status: AssetPartitionStatus[]): CSSProperties => {
  if (status.length === 0) {
    return {background: Colors.Gray200};
  }
  if (status.length === 1) {
    return {background: assetPartitionStatusToColor(status[0])};
  }
  const a = assetPartitionStatusToColor(status[0]);
  const b = assetPartitionStatusToColor(status[1]);

  return {
    background: `linear-gradient(135deg, ${a} 25%, ${b} 25%, ${b} 50%, ${a} 50%, ${a} 75%, ${b} 75%, ${b} 100%)`,
    backgroundSize: '8.49px 8.49px',
  };
};
