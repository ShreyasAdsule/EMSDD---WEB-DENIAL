I have provided the cloned version of the repo used to exploit the session cookies, all other attack attemps were done using console or more manual approaches. We did not need to change any of the 

To use the tool, follow this documentation:https://noraj.github.io/flask-session-cookie-manager/

An example of executing the code is using: 
python flask_session_cookie_manager3.py encode -s 'your_secret_key' -t "{'captcha_answer': '14','captcha_q': '8 + 6','username': 'admin'}"

This will generate a session cookie that can replace your current cookie and allow you to access the admin login, captcha in theory could be changed as long as the logic matches for the validation.

Ensure you have all required libraries installed when running this exploit.

