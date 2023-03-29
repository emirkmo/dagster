import json

from dagster._core.definitions.decorators import op
from dagster._core.execution.context.invocation import build_op_context
from dagster_dbt import dbt_cli_resource


def get_dbt_resource(project_dir, profiles_dir, **kwargs):
    kwargs = kwargs or {}
    return dbt_cli_resource.configured(
        {
            "project_dir": project_dir,
            "profiles_dir": profiles_dir,
            **kwargs,
        }
    )


def get_dbt_solid_context(project_dir, profiles_dir, **kwargs):
    return build_op_context(
        resources={"dbt": get_dbt_resource(project_dir, profiles_dir, **kwargs)}
    )


def test_unconfigured(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run(project_dir=test_project_dir, profiles_dir=dbt_config_dir)

    context = build_op_context(resources={"dbt": dbt_cli_resource})
    dbt_result = my_dbt_solid(context)

    assert len(dbt_result.result["results"]) == 4


def test_seed(test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.seed()

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 1


def test_ls(test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.ls()

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.raw_output.split("\n\n")) == 25


def test_ls_resource_type(test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.ls(resource_type="model")

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.raw_output.split("\n\n")) == 6


def test_test(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        context.resources.dbt.run()
        return context.resources.dbt.test()

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 17


def test_basic_run(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run()

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 4


def test_models_run(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run(models=["least_caloric"])

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 1


def test_models_default_run(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run()

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir, models=["least_caloric"])
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 1


def test_docs_url_run(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run()

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir, docs_url="foo.com")
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 4
    assert dbt_result.docs_url == "foo.com"


def test_models_override_run(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run(models=["least_caloric"])

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir, models=["this_model_is_fake"])
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 1


def test_models_removed_for_run_operation(dbt_seed, test_project_dir, dbt_config_dir):
    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run_operation("log_macro", args={"msg": "foo"})

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir, models=["least_caloric"])
    dbt_result = my_dbt_solid(context)

    assert "--models" not in dbt_result.command
    assert "least_caloric" not in dbt_result.command


def test_extra_args_run(dbt_seed, test_project_dir, dbt_config_dir):
    my_vars = {"foo": 1, "bar": "baz"}

    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run(vars=my_vars)

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)
    assert len(dbt_result.result["results"]) == 4
    assert json.loads(dbt_result.result["args"]["vars"]) == my_vars


def test_models_and_extra_run(dbt_seed, test_project_dir, dbt_config_dir):
    my_vars = {"foo": 1, "bar": "baz"}

    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run(models=["+least_caloric"], vars=my_vars)

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)

    assert len(dbt_result.result["results"]) == 2
    assert json.loads(dbt_result.result["args"]["vars"]) == my_vars


def test_exclude_run(dbt_seed, test_project_dir, dbt_config_dir):
    my_vars = {"foo": 1, "bar": "baz"}

    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run(exclude=["least_caloric"], vars=my_vars)

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir)
    dbt_result = my_dbt_solid(context)

    assert len(dbt_result.result["results"]) == 3
    assert json.loads(dbt_result.result["args"]["vars"]) == my_vars


def test_merged_extra_flags_run(dbt_seed, test_project_dir, dbt_config_dir):
    configured_vars = {"hello": "world"}
    my_vars = {"foo": 1, "bar": "baz"}

    @op(required_resource_keys={"dbt"})
    def my_dbt_solid(context):
        return context.resources.dbt.run(vars=my_vars)

    context = get_dbt_solid_context(test_project_dir, dbt_config_dir, vars=configured_vars)
    dbt_result = my_dbt_solid(context)

    assert len(dbt_result.result["results"]) == 4
    for key in my_vars.keys():
        assert key in dbt_result.command
    assert json.loads(dbt_result.result["args"]["vars"]) == my_vars
