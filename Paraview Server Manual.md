# this is the instruction on setting up the apache and paraview servers
## 1. paraview:
* download `ParaView-5.7.0-RC2-osmesa-MPI-Linux-Python3.7-64bit.tar.gz` for linux from [Paraview Website](https://www.paraview.org/download/)

* extract the file to your `{$MainDirectory}` using `tar -xzvf ParaView-5.7.0-RC2-osmesa-MPI-Linux-Python3.7-64bit.tar.gz`

* rename the extracted folder to `ParaView-5.7.0` using `sudo mv ParaView-5.7.0-RC2-osmesa-MPI-Linux-Python3.7-64bit ParaView-5.7.0`
## 2. Installing apache2 on ubuntu wsl:

a useful instruction for setting up apache on wsl can be found [here](https://learn.getgrav.org/16/webservers-hosting/windows-subsystem-for-linux)

####Steps:
1. install apache2 by: `sudo apt install apache2`

Create a project folder for your websites. This folder needs to be outside of the WSL filesystem. We will use the following directory in this manual: `{$MainDirectory}/ApacheWeb/webroot`.

2. `sudo ln -s {$MainDirectory}/ApacheWeb/webroot /var/www/webroot`

For your future Grav sites to work properly, the Apache module rewrite needs to be enabled.

3. `sudo a2enmod rewrite`

## 3. setting up paraview visualizer server:
make sure you have ParaView-5.7.0 directory
1. create a directory named `{$MainDirectory}/ParaView-5.7.0/viz-logs`
2. create a file named `{$MainDirectory}\ParaView-5.7.0\launcher.config` in ParaView-5.7.0 directory
3. copy following statements in `launcher.config`:
    make sure to replace your main project directory path `{$MainDirectory}`
    ```
    {
    // ===============================
    //General launcher configuration
    // ===============================

    "configuration": {
        "host" : "localhost",                           // name of network interface to bind for launcher webserver
        "port" : 8080,                                  // port to bind for launcher webserver
        "endpoint": "paraview",                         // SessionManager Endpoint
        "content": "{$MainDirectory}/ApacheWeb/webroot",                          // Optional: Directory shared over HTTP
        "proxy_file" : "{$MainDirectory}/ApacheWeb/mapping/proxy.txt",  // Proxy-Mapping file for Apache
        "sessionURL" : "ws://${host}:${port}/ws",       // ws url used by the client to connect to started process
        "timeout" : 5,                                  // Wait time in second after process start
        "log_dir" : "{$MainDirectory}/ParaView-5.7.0/viz-logs",                    // Directory for log files
        "fields" : ["file", "host", "port", "updir"]    // Fields not listed are filtered from response
    },

    // ===============================
    // Resources list for applications
    // ===============================

    "resources" : [ { "host" : "localhost", "port_range" : [9001, 9003] } ],

    //===============================
    // Set of properties for cmd line
    // ===============================

    "properties" : {
        "build_dir" : "{$MainDirectory}/ParaView-5.7.0/",
        "python_exec" : "{$MainDirectory}/ParaView-5.7.0/bin/pvpython",
        "WWW" : "{$MainDirectory}/ParaView-5.7.0/share/paraview-5.7/web/visualizer/www",
        "source_dir": "/.../src"
    },

    //===============================
    // Application list with cmd line
    // ===============================

    "apps": {
        "visualizer": {
            "cmd": [
                "${python_exec}",
                "-dr", "{$MainDirectory}/ParaView-5.7.0/share/paraview-5.7/web/visualizer/server/pvw-visualizer.py",
                "--port", "${port}",
                "--data", "{$MainDirectory}/media/32/results/",
                "-f",
                "--authKey", "${secret}"
            ],
            "ready_line" : "Starting factory"
        }
    }
    }
    ```
###### make sure <span style="color:blue">line 45</span> is `"--data", "{$MainDirectory}/media/32/results/",`
* main source of documentation is [here](https://kitware.github.io/visualizer/docs/apache_front_end.html)

3. Configure Apache httpd for use with ParaViewWeb:
* create a file named  `proxy.txt` in a directory at main folder named `{$MainDirectory}/ApacheWeb/mapping/proxy.txt` by following commands (make sure you are at the project's main directory):
* `sudo mkdir -p {$MainDirectory}/ApacheWeb/mapping`
* go to mapping directory and create a file named proxy.txt
* `sudo touch proxy.txt`

run following commands and replace `{$pvw-user}` with your ubuntu username:

* `sudo groupadd mappingfileusers`
* `sudo usermod -a -G mappingfileusers {$pvw-user}`
* `newgrp mappingfileusers`
* `sudo usermod -a -G mappingfileusers daemon`
* `sudo chgrp mappingfileusers ApacheWeb/mapping/proxy.txt`
* `sudo chmod 660 ApacheWeb/mapping/proxy.txt`

### adding a virtual host to apache:

* create a virtual host configuration:
- `sudo touch /etc/apache2/sites-available/001-pvw.conf`
- `sudo nano /etc/apache2/sites-available/001-pvw.conf`
* create two files `{$MainDirectory}/ApacheWeb/error.log` and `{$MainDirectory}/ApacheWeb/access.log`
* replace following content within the file:
make sure you replace `{$MainDirectory}` to main directory.

```
<VirtualHost *:80>
    ServerName localhost
    ServerAdmin webmaster@example-host.example.com
    DocumentRoot {$MainDirectory}/ApacheWeb/webroot/
    ErrorLog {$MainDirectory}/ApacheWeb/error.log
    CustomLog {$MainDirectory}/ApacheWeb/access.log combined

    ### The following commented lines could be useful when running
    ### over https and wss:
    # SSLEngine On
    # SSLCertificateFile    /etc/apache2/ssl/your_certificate.crt
    # SSLCertificateKeyFile /etc/apache2/ssl/your_domain_key.key
    # SSLCertificateChainFile /etc/apache2/ssl/DigiCertCA.crt
    #
    # <Location ${DocumentRoot} >
    #   SSLRequireSSL On
    #   SSLVerifyClient optional
    #   SSLVerifyDepth 1
    #   SSLOptions +StdEnvVars +StrictRequire
    # </Location>

    # Rule for ParaViewWeb launcher
    ProxyPass /paraview http://localhost:9000/paraview

    # Rewrite setup for ParaViewWeb
    RewriteEngine On

    # This is the path the mapping file Jetty creates
    RewriteMap session-to-port txt:{$MainDirectory}/ApacheWeb/mapping/proxy.txt

    # This is the rewrite condition. Look for anything with a sessionId= in the query part of the URL and capture the value to use below.
    RewriteCond %{QUERY_STRING}     ^sessionId=(.*)&path=(.*)$ [NC]

    # This does the rewrite using the mapping file and the sessionId
    RewriteRule    ^/proxy.*$  ws://${session-to-port:%1}/%2  [P]

    <Directory "${DocumentRoot}">
        Options Indexes FollowSymLinks
        Order allow,deny
        Allow from all
        AllowOverride None
        Require all granted
    </Directory>
    
</VirtualHost>
```
* you will need to enable the modules that will be used by our ParaViewWeb virtual host
- `sudo a2enmod vhost_alias`
- `sudo a2enmod proxy`
- `sudo a2enmod proxy_http`
- `sudo a2enmod proxy_wstunnel`
- `sudo a2enmod rewrite`

* Add the following line to the end of `/etc/apache2/apache2.conf`
`AcceptFilter http none`

* Then enable the virtual host you created above and restart Apache
- `sudo a2ensite 001-pvw.conf`
- `sudo a2dissite 000-default.conf`
- `sudo service apache2 restart`


# Celery Manual
version:4.3
https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
https://github.com/celery/celery/tree/master/examples/django

requirements:

`pip install django-celery-results`
## In a production environment you’ll want to run the worker in the background as a daemon - see Daemonization 

#Redis : message broker:
https://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html#broker-redis

`sudo apt-get install redis-server`
`sudo service redis-server start`   \\\ sudo service redis-server  {start|stop|restart|force-reload|status}

`pip install -U "celery[redis]"`

run the server: `celery -A ASC_Project worker -l info`

https://stackoverflow.com/questions/38267525/how-to-make-celery-worker-return-results-from-task

# Monitoring tasks:
supervisor version: 3.3.1

`sudo apt-get install supervisor`
https://pinoylearnpython.com/django-celery-with-real-time-monitoring-tasks-using-flower/