<?php
$config['product_name'] = 'riverxia mail';
$config['support_url'] = '';
$config['login_autocomplete'] = 0;
$config['refresh_interval'] = 60;
$config['draft_autosave'] = 60;
$config['session_lifetime'] = 10080; // minutes (7 days)
$config['message_show_email'] = true;
$config['skin_logo'] = ['*' => ''];
// log in to SMTP (submission requires auth) with the same credentials as IMAP
$config['smtp_user'] = '%u';
$config['smtp_pass'] = '%p';
$config['smtp_auth_type'] = 'LOGIN';
