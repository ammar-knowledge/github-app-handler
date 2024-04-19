from githubapp import EventCheckRun


def test_start_check_run(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start()

    check_run.repository.create_check_run.assert_called_once_with(
        "name", "sha", status="in_progress", output={"title": "name", "summary": ""}
    )


def test_start_check_run_with_summary_and_text(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start(title="title", summary="summary", text="text")
    check_run.repository.create_check_run.assert_called_with(
        "name",
        "sha",
        status="in_progress",
        output={"title": "title", "summary": "summary", "text": "text"},
    )


def test_update_check_run_with_only_status(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start("name", "sha", "title")
    check_run.update(status="status")
    check_run.check_run.edit.assert_called_with(status="status")


def test_update_check_run_with_only_conclusion(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start("name", "sha", "title")
    check_run.update(conclusion="conclusion")
    check_run.check_run.edit.assert_called_with(status="completed", conclusion="conclusion")


def test_update_check_run_with_output(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start("name", "sha", "title", "summary")
    check_run.update(title="new_title", summary="new_summary")
    check_run.check_run.edit.assert_called_with(output={"title": "new_title", "summary": "new_summary"})


def test_update_check_run_with_only_output_text(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start("name", "sha", "title")
    check_run.check_run.output.title = "title"
    check_run.check_run.output.summary = "summary"
    check_run.update(text="text")
    check_run.check_run.edit.assert_called_with(output={"title": "title", "summary": "summary", "text": "text"})


def test_update_check_run_with_nothing(event):
    check_run = EventCheckRun(event.repository, "name", "sha")
    check_run.start("name", "sha", "title")
    check_run.update()
    check_run.check_run.edit.assert_not_called()
