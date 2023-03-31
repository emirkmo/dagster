from enum import Enum
from typing import Any, Dict

import pytest
from dagster import Config, RunConfig, config_mapping, job, op
from dagster._check import CheckError


def test_binding_runconfig() -> None:
    class DoSomethingConfig(Config):
        config_param: str

    @op
    def do_something(config: DoSomethingConfig) -> str:
        return config.config_param

    @job(config=RunConfig(ops={"do_something": DoSomethingConfig(config_param="foo")}))  # type: ignore[call-arg]
    def do_it_all_with_baked_in_config() -> None:
        do_something()

    result = do_it_all_with_baked_in_config.execute_in_process()
    assert result.success
    assert result.output_for_node("do_something") == "foo"


def test_binding_runconfig_more_complex() -> None:
    class DoSomethingConfig(Config):
        config_param: str

    @op
    def do_something(config: DoSomethingConfig) -> str:
        return config.config_param

    class DoSomethingElseConfig(Config):
        x: int
        y: int

    @op
    def do_something_else(config: DoSomethingElseConfig) -> int:
        return config.x + config.y

    @job(
        config=RunConfig(  # type: ignore[call-arg]
            ops={
                "do_something": DoSomethingConfig(config_param="foo"),
                "do_something_else": DoSomethingElseConfig(x=3, y=4),
            }
        )
    )
    def do_it_all_with_baked_in_config() -> None:
        do_something()
        do_something_else()

    result = do_it_all_with_baked_in_config.execute_in_process()
    assert result.success
    assert result.output_for_node("do_something") == "foo"
    assert result.output_for_node("do_something_else") == 7


def test_config_mapping_return_config_dict() -> None:
    class DoSomethingConfig(Config):
        config_param: str

    @op
    def do_something(config: DoSomethingConfig) -> str:
        return config.config_param

    class ConfigMappingConfig(Config):
        simplified_param: str

    # New, fancy config mapping takes in a Pythonic config object but returns normal config dict
    @config_mapping
    def simplified_config(config_in: ConfigMappingConfig) -> Dict[str, Any]:
        return {"ops": {"do_something": {"config": {"config_param": config_in.simplified_param}}}}

    @job(config=simplified_config)
    def do_it_all_with_simplified_config() -> None:
        do_something()

    result = do_it_all_with_simplified_config.execute_in_process(
        run_config={"simplified_param": "foo"}
    )
    assert result.success
    assert result.output_for_node("do_something") == "foo"


def test_config_mapping_return_run_config() -> None:
    class DoSomethingConfig(Config):
        config_param: str

    @op
    def do_something(config: DoSomethingConfig) -> str:
        return config.config_param

    class ConfigMappingConfig(Config):
        simplified_param: str

    # New, fancy config mapping takes in a Pythonic config object and returns a RunConfig
    @config_mapping
    def simplified_config(config_in: ConfigMappingConfig) -> RunConfig:
        return RunConfig(
            ops={"do_something": DoSomethingConfig(config_param=config_in.simplified_param)}
        )

    @job(config=simplified_config)
    def do_it_all_with_simplified_config() -> None:
        do_something()

    result = do_it_all_with_simplified_config.execute_in_process(
        run_config={"simplified_param": "foo"}
    )
    assert result.success
    assert result.output_for_node("do_something") == "foo"


def test_config_mapping_config_schema_errs() -> None:
    class DoSomethingConfig(Config):
        config_param: str

    @op
    def do_something(config: DoSomethingConfig) -> str:
        return config.config_param

    class ConfigMappingConfig(Config):
        simplified_param: str

    # No need to specify config_schema when supplying a Pythonic config object
    with pytest.raises(CheckError):

        @config_mapping(config_schema={"simplified_param": str})
        def simplified_config(config_in: ConfigMappingConfig) -> RunConfig:
            return RunConfig(
                ops={"do_something": DoSomethingConfig(config_param=config_in.simplified_param)}
            )


def test_config_mapping_enum() -> None:
    class MyEnum(Enum):
        FOO = "foo"
        BAR = "bar"

    class DoSomethingConfig(Config):
        config_param: MyEnum

    @op
    def do_something(config: DoSomethingConfig) -> MyEnum:
        return config.config_param

    class ConfigMappingConfig(Config):
        simplified_param: MyEnum

    @config_mapping
    def simplified_config(config_in: ConfigMappingConfig) -> Dict[str, Any]:
        return {
            "ops": {"do_something": {"config": {"config_param": config_in.simplified_param.name}}}
        }

    @job(config=simplified_config)
    def do_it_all_with_simplified_config() -> None:
        do_something()

    result = do_it_all_with_simplified_config.execute_in_process(
        run_config={"simplified_param": "FOO"}
    )
    assert result.success
    assert result.output_for_node("do_something") == MyEnum.FOO
