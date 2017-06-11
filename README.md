INSTALL & RUN
-----------------

The preferred way of testing any assignment is with the help of virtualenv. Follow these simple steps:
* Create a new python environment
with command `virtualenv {envname}`
* Install prerequisites. You do it with the command
`{envname}/bin/pip install {project_directory}/requirements.txt` 
* After installing the prerequisites, you can run the API
server with the command `{envname}/bin/python {project_directory}/main.py`

After those steps you will see a message 
> &ast; Running on https://0.0.0.0:8080/ (Press CTRL+C to quit)

Now the API server is running and you can start using it.

USE
---

#### POST /login

I added two additional end points so that the user can authorize and deauthorize himself/herself. The first additional
end point is `/login`, and you need to provide your credentials in the POST body. 

###### Example usage:

<pre><code>curl -i -k -H "Content-Type: application/json" -X POST -d  '{"login":"user1", "password":"qwerty1", "duration": 3 }' https://0.0.0.0:8080/login</pre></code>

Note that you need to use `-k` option, because the API server is using HTTPS protocol, but the certificate is self-signed, so
curl or web browser will complain about certificate. `-k` option allows connections to SSL sites without trusted certificates.

The `duration` parameter is not mandatory, the meaning of this parameter is how long (in hours) are you  planning to use the API server before logging out.
If you don't specify the parameter, when API server assumes that you want to use it for one hour and after one hour you are logged out automatically. 
Response from the server is a dictionary with two keys - `session_id` and `expires`.

Note that I am using login `login1` and password `qwerty1`. For your convenience, I added 200 uniform users  with login `login{n}` and password `qwerty{n}`.
Normally, users should perform registration by themselves and choose a more secure password (and server should reject too simple passwords).

###### Response
{String} session_id

{String} expires Timestamp when your session expires

###### Example:
<pre><code>{
  "expires": "2017-06-11 23-15-21",
  "session_id": "e87659c517874dec913ad4e26c69aa4a"
}
</pre></code>

#### POST /logout

The second additional end point is `/logout` and you can use it if you want to terminate your session immediately.

###### Example usage:

<pre><code>curl -i -k -H "Content-Type: application/json" -X POST -d  '{"session_id": "7e43e2da261346c1858a6d8aa33cceeb" }' https://0.0.0.0:8080/logout</pre></code>

The response is always empty dictionary.

#### GET /limits, GET /data

The two remaining end points are `/limits` and `/data`. They are well described in the assignment text. I made only one modification. Both end points now require additional parameter `session_id`.

###### Example usage:

<pre><code>curl -i -k "https://0.0.0.0:8080/data?count=5&start=2011-01-01&resolution=M&session_id=7e43e2da261346c1858a6d8aa33cceeb"</pre></code>
<pre><code>curl -i -k "https://0.0.0.0:8080/limits?session_id=7e43e2da261346c1858a6d8aa33cceeb"</pre></code>
 