# -*- coding: iso8859-15 -*-
import os
import sys


appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)


from global_config import EMAIL_HOST_USER, DBSession

def get_footer():
    from upstage_options.db_models.config import ConfigModel
    from upstage_options.services.upstage_option import ADDING_EMAIL_SIGNATURE, EMAIL_SIGNATURE

    addingSignatureEmail = DBSession.query(ConfigModel).filter(ConfigModel.name == ADDING_EMAIL_SIGNATURE).first()
    if addingSignatureEmail.value != "true":
        return ""
    
    signature = DBSession.query(ConfigModel).filter(ConfigModel.name == EMAIL_SIGNATURE).first()
    return signature.value


def display_user(user):
    return user.display_name if user.display_name else user.username


def password_reset(user, otp):
    return f"""
<p>
Hi <b>{display_user(user)}</b>,
<br>
<br>
We received a request to reset your forgotten password. Please use the following code for your password reset:
<b style="color: #007011">{otp}</b>
<br>
The code will expire in 30 minutes.
<br>
<br>
If you did not request a password reset, please ignore this email.
<br>
<br>
{get_footer()}
"""


def user_registration(user):
    return f"""
<p>
Hi <b>{display_user(user)}</b>,
<br>
<br>
We are glad that you're here! Your account has been created and waiting for approval by an UpStage Admin. You will receive an email once your account has been approved.
<br>
<br>
Please look at the <a href="https://docs.upstage.live/">UpStage User Manual</a> for documentation on how to use UpStage.
<br>
<br>
If you have any questions, please contact us at <a href="mailto:{EMAIL_HOST_USER}">{EMAIL_HOST_USER}</a>.
<br>
<br>
{get_footer()}
"""


def user_approved(user):
    return f"""
<p>
Hi <b>{display_user(user)}</b>,
<br>
<br>
Thank you for registering with us. Your account has been approved! You can now login to UpStage.
<br>
<br>
Here is your account information:
<br>
<br>
<b>Username:</b> {user.username}
<br>
<b>Password:</b> <i>the one you used to register</i>. If you forgot your password, click on the "Forgot Password" link on the login page.
<br>
<br>
{get_footer()}
"""


def admin_registration_notification(user, approval_url):
    return f"""
<p>
Dear Admins,
<br>
<br>
A new user has registered with UpStage. Please approve the user by clicking on the following link:
<br>
<br>
<a href="{approval_url}">{approval_url}</a>
<br>
<br>
The user's information is:
<br>
<br>
<b>Username:</b> {user.username}
<br>
<b>Full Name:</b> {user.first_name} {user.last_name}
<br>
<b>Email:</b> {user.email}
<br>
<b>Introduction:</b> {user.intro}
<br>
<br>
{get_footer()}
"""


def request_permission_for_media(user, media, note, studio_url):
    return f"""
<p>
Hi <b>{display_user(media.owner)}</b>,
<br>
<br>
{display_user(user)} has requested permission to use your media <b>{media.name}</b>. Please go to the <a href="{studio_url}">Studio</a> and click on the Notification icon to approve or deny the request.
<br>
Purpose: {note}
<br>
<br>
<br>
<br>
{get_footer()}
"""


def waiting_request_media_approve(user, media):
    return f"""
<p>
Hi <b>{display_user(user)}</b>,
<br>
<br>
Your permission request to use media <b>{media.name}</b> has been sent to the owner. Please wait for a response.
<br>
<br>
<br>
<br>
{get_footer()}
"""


def request_permission_acknowledgement(user, media, note="", description=""):
    return f"""
<p>
Hi <b>{display_user(user)}</b>,
<br>
<br>
You have agreed to acknowledge use of <b>{media.name}</b>.
<br>
<br>
Additional notes: {note}
<br>
{description}
<br>
<br>
<br>
{get_footer()}    
"""


def permission_response_for_media(user, media, note, approved, studio_url):
    return f"""
<p>
Hi <b>{display_user(user)}</b>,
<br>
<br>
Your permission request for <b>{media.name}</b> with purpose \"{note}\" has been {"approved" if approved else "denied"} by the owner.
{f'<br><br>You can now use the media in the <a href="{studio_url}">Studio</a>.' if approved else ""}
<br>
<br>
<br>
<br>
{get_footer()}
"""


def notify_owner_of_media_request(user, media):
    return f"""
<p>
Hi <b>{display_user(media.owner)}</b>,
<br>
<br>
{display_user(user)} is using your media {media.name} and has agreed to acknowledge it as you require.
<br>
<br>
{get_footer()}
"""


def notify_mark_media_active(media):
    return f"""
<p>
Hi <b>{display_user(media.owner)}</b>,
<br>
<br>
Your dormant media item  {media.name} has been reactivated. You will find it in your Media list and can now edit and assign it to stages
<br>
<br>
{get_footer()}
"""
