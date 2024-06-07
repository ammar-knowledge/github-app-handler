from unittest.mock import Mock, patch

import pytest
from github.CheckRun import CheckRun

from githubapp import Config, EventCheckRun
from githubapp.event_check_run import ICONS_DEFAULT, CheckRunConclusion, CheckRunStatus


@pytest.fixture(autouse=True)
def mock_check_run(event):
    repository = event.repository
    repository.create_check_run.return_value = Mock(output=Mock(title=None, summary=None))


@pytest.mark.parametrize(
    "sub_runs_icons,expected_icons",
    [
        (None, {}),
        ("circle", ICONS_DEFAULT["circle"]),
        ({"key": "value"}, {"key": "value"}),
        ("nonexistent", AttributeError),
        (12, AttributeError),
    ],
    ids=[
        "No config",
        "Config as string",
        "Config as dict",
        "Config as nonexistent string",
        "Config not as string nor dict",
    ],
)
def test_set_icons(sub_runs_icons, expected_icons):
    with patch.object(Config, "SUB_RUNS_ICONS", sub_runs_icons), patch.object(EventCheckRun, "icons", {}):
        if expected_icons == AttributeError:
            with pytest.raises(expected_icons):
                EventCheckRun.set_icons()
        else:
            EventCheckRun.set_icons()
            assert EventCheckRun.icons == expected_icons


def test_start_check_run(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start()

    check_run.repository.create_check_run.assert_called_once_with(
        "name", "sha", status="waiting", output={"title": "name", "summary": ""}
    )


def test_start_check_run_with_summary_and_text(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title", summary="summary", text="text")
    check_run.repository.create_check_run.assert_called_with(
        "name",
        "sha",
        status="waiting",
        output={"title": "title", "summary": "summary", "text": "text"},
    )


def test_update_check_run_with_only_status(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title")
    check_run.update(status=CheckRunStatus.QUEUED)
    check_run._check_run.edit.assert_called_with(status="queued")


def test_update_check_run_with_only_conclusion(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title")
    check_run.update(conclusion=CheckRunConclusion.SUCCESS)
    check_run._check_run.edit.assert_called_with(status="completed", conclusion="success")


def test_update_check_run_with_output(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title", summary="summary")
    check_run.update(title="new_title", summary="new_summary")
    check_run._check_run.edit.assert_called_with(output={"title": "new_title", "summary": "new_summary"})


def test_update_check_run_with_only_output_text(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title")
    check_run._check_run.output.title = "title"
    check_run._check_run.output.summary = "summary"
    check_run.update(text="text")
    check_run._check_run.edit.assert_called_with(output={"title": "title", "summary": "summary", "text": "text"})


def test_update_check_run_with_nothing(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title")
    check_run.update()
    check_run._check_run.edit.assert_not_called()


def test_sub_check_run(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title")
    sub_run1 = check_run.create_sub_run("sub 1")
    sub_run2 = check_run.create_sub_run("sub 2")
    sub_run1.update(title="sub 1 title", summary="sub 1 summary")
    check_run_edit = check_run._check_run.edit
    check_run_edit.assert_called_once_with(
        output={
            "title": "sub 1 title",
            "summary": "sub 1: sub 1 title\nsub 1 summary\nsub 2: ",
        }
    )
    check_run_edit.reset_mock()
    sub_run2.update(title="sub 2 title", summary="sub 2 summary")
    check_run_edit.assert_called_once_with(
        output={
            "title": "sub 2 title",
            "summary": "sub 1: sub 1 title\nsub 1 summary\nsub 2: sub 2 title\nsub 2 summary",
        }
    )
    check_run_edit.reset_mock()
    sub_run1.update(title="sub 1 title", summary="sub 1 other summary", update_check_run=False)
    check_run_edit.assert_not_called()
    sub_run2.update(title="sub 2 title", summary="sub 2 other summary")
    check_run_edit.assert_called_once_with(
        output={
            "title": "sub 2 title",
            "summary": "sub 1: sub 1 title\nsub 1 other summary\nsub 2: sub 2 title\nsub 2 other summary",
        }
    )


def test_sub_check_run_icons(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title")
    sub_run1 = check_run.create_sub_run("sub 1")
    icons = {e: e.value for e in list(CheckRunStatus) + list(CheckRunConclusion)}
    with patch.object(EventCheckRun, "icons", icons):
        for status in CheckRunStatus:
            sub_run1.update(status=status)
            check_run._check_run.edit.assert_called_with(output={"summary": f":{status.value}: sub 1: "})
        for conclusion in CheckRunConclusion:
            sub_run1.update(conclusion=conclusion)
            check_run._check_run.edit.assert_called_with(output={"summary": f":{conclusion.value}: sub 1: "})


def test_check_run_getattr(event):
    mocked_check_run = CheckRun(
        requester=Mock(),
        headers={},
        attributes={
            "status": "queued",
            "conclusion": "success",
            "output": {"title": "title"},
        },
        completed=True,
    )
    with patch.object(event.repository, "create_check_run", return_value=mocked_check_run):
        check_run = EventCheckRun(event.repository, "name", "sha")
        assert check_run.anny_attr is None
        check_run.start()
        assert check_run.status == CheckRunStatus.QUEUED
        assert check_run.conclusion == CheckRunConclusion.SUCCESS
        assert check_run.title == "title"
        with pytest.raises(AttributeError):
            assert check_run.nonexistent


@pytest.mark.parametrize(
    "conclusion,expected_title",
    [
        (None, "Stale"),
        (CheckRunConclusion.SUCCESS, "Done"),
        (CheckRunConclusion.SKIPPED, "Skipped"),
        (CheckRunConclusion.CANCELLED, "Cancelled"),
    ],
)
def test_finish_check_run(event, conclusion, expected_title):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start()
    check_run.finish(conclusion=conclusion)
    expected_conclusion = conclusion.value if conclusion else "stale"
    check_run._check_run.edit.assert_called_once_with(
        status="completed",
        conclusion=expected_conclusion,
        output={"title": expected_title},
    )


@pytest.mark.parametrize(
    "conclusion,expected_conclusion,expected_title,sub_run1_initial_conclusion,sub_run2_initial_conclusion",
    [
        (None, CheckRunConclusion.CANCELLED, "sub 1: Cancelled", None, None),
        (
            CheckRunConclusion.SUCCESS,
            CheckRunConclusion.CANCELLED,
            "sub 1: Cancelled",
            None,
            None,
        ),
        (
            CheckRunConclusion.SUCCESS,
            CheckRunConclusion.CANCELLED,
            "Sub 2 title",
            CheckRunConclusion.SKIPPED,
            None,
        ),
        (
            CheckRunConclusion.SUCCESS,
            CheckRunConclusion.FAILURE,
            "Sub 2 title",
            CheckRunConclusion.SKIPPED,
            CheckRunConclusion.FAILURE,
        ),
        (
            CheckRunConclusion.SUCCESS,
            CheckRunConclusion.SUCCESS,
            "Done",
            CheckRunConclusion.SUCCESS,
            CheckRunConclusion.SUCCESS,
        ),
        (
            CheckRunConclusion.SUCCESS,
            CheckRunConclusion.CANCELLED,
            "Sub 2 title",
            CheckRunConclusion.STALE,
            CheckRunConclusion.CANCELLED,
        ),
        (
            CheckRunConclusion.FAILURE,
            CheckRunConclusion.FAILURE,
            "Failure",
            CheckRunConclusion.STALE,
            CheckRunConclusion.CANCELLED,
        ),
    ],
)
def test_finish_check_run_with_sub_runs(
    event,
    conclusion,
    expected_conclusion,
    expected_title,
    sub_run1_initial_conclusion,
    sub_run2_initial_conclusion,
):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start()
    sub_run1 = check_run.create_sub_run("sub 1")
    sub_run2 = check_run.create_sub_run("sub 2")

    sub_run1.update(conclusion=sub_run1_initial_conclusion, update_check_run=False)
    sub_run2.update(title=f"Sub 2 title", conclusion=sub_run2_initial_conclusion, update_check_run=False)
    check_run.finish(conclusion=conclusion)

    check_run._check_run.edit.assert_called_once_with(
        status="completed",
        conclusion=expected_conclusion.value,
        output={"summary": "sub 1: \nsub 2: Sub 2 title", "title": expected_title},
    )
    assert sub_run1.conclusion == sub_run1_initial_conclusion or CheckRunConclusion.CANCELLED
    assert sub_run2.conclusion == sub_run2_initial_conclusion or CheckRunConclusion.CANCELLED
