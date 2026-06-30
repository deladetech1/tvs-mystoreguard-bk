_KIND_COPY = {
    "ASSIGNED": ("A task is pending on you", "#1a73e8",
                 "A new step has been assigned to you and is ready to be picked up."),
    "READY": ("A task step is ready for you", "#1a73e8",
              "A step you're assigned to is now ready to be worked on."),
    "DONE_NEEDS_APPROVAL": ("A step needs your approval", "#fd7e14",
                            "A step has been marked done and is waiting for you to approve it."),
    "REMINDER": ("Reminder: a task is still pending on you", "#dc3545",
                 "This step is still waiting on you. Please action it when you can."),
    "MENTIONED": ("You were mentioned in a task comment", "#6f42c1",
                  "Someone mentioned you in a comment on this task. Open it to see the discussion."),
}


def build_task_notification_email_html(kind: str, recipient_name: str | None, task: dict) -> tuple[str, str]:
    """Return (subject, html_body) for a task notification email."""
    heading, color, blurb = _KIND_COPY.get(kind, _KIND_COPY["READY"])
    title = task.get("title") or "Task"
    step_name = task.get("step_name")
    due = task.get("due_date")

    step_row = ""
    if step_name:
        step_row = f"""
        <tr>
            <td style="padding: 8px 0; color: #666;">Step</td>
            <td style="padding: 8px 0; font-weight: bold;">{step_name}</td>
        </tr>"""
    due_row = ""
    if due:
        due_row = f"""
        <tr>
            <td style="padding: 8px 0; color: #666;">Due</td>
            <td style="padding: 8px 0; font-weight: bold;">{due}</td>
        </tr>"""

    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    subject = f"{heading}: {title}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
            <h2 style="color: {color}; margin-top: 0;">{heading}</h2>
            <p>{greeting}</p>
            <p>{blurb}</p>
            <div style="background-color: #ffffff; padding: 16px; border-radius: 4px; border: 1px solid #e9ecef;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #666;">Job</td>
                        <td style="padding: 8px 0; font-weight: bold;">{title}</td>
                    </tr>
                    {step_row}
                    {due_row}
                </table>
            </div>
        </div>
        <p style="font-size: 12px; color: #999; margin-top: 16px;">
            This notification was sent via MyStoreGuard.
        </p>
    </body>
    </html>
    """
    return subject, html
