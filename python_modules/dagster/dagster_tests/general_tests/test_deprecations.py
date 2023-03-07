# This file strictly contains tests for deprecation warnings. It can serve as a central record of
# deprecations for the current version.

import re

import pytest
from dagster._core.definitions.schedule_definition import ScheduleDefinition

# ########################
# ##### SCHEDULE ENV VARS
# ########################


def test_schedule_environment_vars():
    with pytest.warns(DeprecationWarning, match=re.escape("environment_vars")):
        ScheduleDefinition(
            name="foo",
            cron_schedule="@daily",
            job_name="bar",
            environment_vars={"foo": "bar"},
        )
