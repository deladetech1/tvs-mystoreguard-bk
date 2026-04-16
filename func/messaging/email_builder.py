def build_message_email_html(subject: str, body: str) -> str:
    """Build an HTML email for a direct message to a supplier or customer."""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
            <h2 style="color: #2c3e50; margin-top: 0;">{subject}</h2>
            <div style="background-color: #ffffff; padding: 16px; border-radius: 4px; border: 1px solid #e9ecef;">
                {body}
            </div>
        </div>
        <p style="font-size: 12px; color: #999; margin-top: 16px;">
            This message was sent via MyStoreGuard.
        </p>
    </body>
    </html>
    """


def build_meeting_reminder_email_html(meeting: dict) -> str:
    """Build an HTML email for a meeting reminder."""
    location_html = ""
    if meeting.get("location"):
        location_html = f"""
        <tr>
            <td style="padding: 8px 0; color: #666;">Location</td>
            <td style="padding: 8px 0; font-weight: bold;">{meeting['location']}</td>
        </tr>
        """

    description_html = ""
    if meeting.get("description"):
        description_html = f"""
        <div style="margin-top: 16px; padding: 12px; background-color: #f8f9fa; border-radius: 4px;">
            <p style="margin: 0; color: #555;">{meeting['description']}</p>
        </div>
        """

    end_time_display = f" – {meeting['end_time']}" if meeting.get("end_time") else ""

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #fff3cd; padding: 16px; border-radius: 8px; border: 1px solid #ffc107; margin-bottom: 16px;">
            <strong>Reminder:</strong> You have an upcoming meeting.
        </div>
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
            <h2 style="color: #2c3e50; margin-top: 0;">{meeting['title']}</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666; width: 100px;">Date</td>
                    <td style="padding: 8px 0; font-weight: bold;">{meeting['meeting_date']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Time</td>
                    <td style="padding: 8px 0; font-weight: bold;">{meeting['start_time']}{end_time_display}</td>
                </tr>
                {location_html}
            </table>
            {description_html}
        </div>
        <p style="font-size: 12px; color: #999; margin-top: 16px;">
            This reminder was sent via MyStoreGuard.
        </p>
    </body>
    </html>
    """


def build_message_sms_text(subject: str, body: str) -> str:
    """Build a plain text SMS for a direct message."""
    return f"{subject}\n\n{body}"


def build_meeting_reminder_sms_text(meeting: dict) -> str:
    """Build a plain text SMS for a meeting reminder."""
    end_time_display = f"-{meeting['end_time']}" if meeting.get("end_time") else ""
    location_display = f" at {meeting['location']}" if meeting.get("location") else ""
    return (
        f"Reminder: {meeting['title']}\n"
        f"Date: {meeting['meeting_date']}\n"
        f"Time: {meeting['start_time']}{end_time_display}{location_display}"
    )
