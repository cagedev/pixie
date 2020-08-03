System: Ubuntu Server 20.04
Hardware: Raspberry pi 3 (1GB) with Adafruit RGBHat

## RGBMatrix (hzeller)

## Using `systemd` to run redis in the background


### rq worker

```console
ubuntu@ubuntu:~/pixie$ sudo sysctl status rqworker@1
● rqworker@1.service - RQ Worker Number 1
     Loaded: loaded (/etc/systemd/system/rqworker@.service; disabled; vendor preset: enabled)
     Active: active (running) since Sat 2020-08-01 19:56:02 UTC; 328ms ago
   Main PID: 6121 (rq)
      Tasks: 1 (limit: 1827)
     CGroup: /system.slice/system-rqworker.slice/rqworker@1.service
             └─6121 /usr/bin/python3 /home/ubuntu/.local/bin/rq worker -c pixie-led.py
```

Seems fine

```console
ubuntu@ubuntu:~/pixie$ rqinfo
default      |███████ 7
1 queues, 7 jobs total
0 workers, 1 queues
Updated: 2020-08-01 19:56:58.238937
```

Why zero workers...?

`sudo ./run_server.sh`

`http://192.168.1.196:5000/pixie/queue?n=10`

Task gets enqueued...

```console
ubuntu@ubuntu:~/pixie$ sudo sysctl status rqworker@1
● rqworker@1.service - RQ Worker Number 1
     Loaded: loaded (/etc/systemd/system/rqworker@.service; disabled; vendor preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Sat 2020-08-01 19:58:48 UTC; 116ms ago
    Process: 6553 ExecStart=/home/ubuntu/.local/bin/rq worker -c pixie-led.py (code=exited, status=1/FAILURE)
   Main PID: 6553 (code=exited, status=1/FAILURE)

Aug 01 19:58:48 ubuntu systemd[1]: rqworker@1.service: Scheduled restart job, restart counter is at 422.
Aug 01 19:58:48 ubuntu systemd[1]: Stopped RQ Worker Number 1.
Aug 01 19:58:48 ubuntu systemd[1]: Started RQ Worker Number 1.

● rqworker@1.service - RQ Worker Number 1
     Loaded: loaded (/etc/systemd/system/rqworker@.service; disabled; vendor preset: enabled)
     Active: active (running) since Sat 2020-08-01 20:00:40 UTC; 1s ago
   Main PID: 6812 (rq)
      Tasks: 2 (limit: 1827)
     CGroup: /system.slice/system-rqworker.slice/rqworker@1.service
             └─6812 /usr/bin/python3 /home/ubuntu/.local/bin/rq worker -c pixie-led.py
```

```console
ubuntu@ubuntu:~/pixie$ redis-cli
127.0.0.1:6379> keys *
 1) "test"
 2) "rq:job:076edf07-700d-4f52-af0a-351321b41579"
 3) "rq:job:8aaa1b79-19ad-46c8-ae87-80112448bd24"
 4) "rq:queue:default"
 5) "rq:job:b0c51c5e-e49e-4dce-8e83-c8cc25e6b7a6"
 6) "rq:job:c0ef598f-db30-4dae-98df-df5e4a8b8d79"
 7) "rq:job:303ca06c-50f1-4833-9eeb-54c236b701bf"
 8) "rq:job:d334556f-c022-44cd-9912-14e82289fe61"
 9) "rq:job:3a42da70-9af7-47b6-99a6-f9f569b25e41"
10) "rq:job:7e670aa7-053a-4375-9bf6-8b954e341b31"
11) "rq:queues"
127.0.0.1:6379>
```

OK... so the python file the worker "runs" is it's config file...

```python
REDIS_URL = 'redis://localhost:6379/1'
QUEUES = ['high', 'default', 'low']
```

No idea how the path works for loading this file, but ignoring the problem and _not_ loading a config seems to pick the correct default.... F*** it, rolling with it.

Picture is messed up when offloaded to background task. Probably due to multitasking on core. Tried setting higher gpio / cpu priorities:

```console
 sudo nano /etc/systemd/system/rqworker@.service
```

```config
[Unit]
Description=RQ Worker Number %i
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/pixie
Environment=LANG=en_US.UTF-8
Environment=LC_ALL=en_US.UTF-8
Environment=LC_LANG=en_US.UTF-8
ExecStart= /home/ubuntu/.local/bin/rq worker
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
PrivateTmp=true
Restart=always
User=root
CPUAffinity=3
CPUQuota=100%
CPUWeight=10000
IOWeight=10000

[Install]
WantedBy=multi-user.target
```

Also set dedicated CPU affinity and isolate that CPU with 

```console
sudo nano /boot/firmware/cmdline.txt
```

```config
... isolcpu=3
```

Now to check performance...

Still glitchy... possibly just go for the (cached) stream creation and then playback as a separate callback task.

For now we'll go with the optimized viewer as a semi-dedicated background task.

```python
os.system("sudo /home/ubuntu/rpi-rgb-led-matrix/utils/led-image-viewer /home/ubuntu/pixie/cache/temp3.gif -t 5 --led-limit-refresh=200 --led-pwm-lsb-nanoseconds=200")
```

Extra options seem to cause it to stay in the loop. It still seems pretty glitchy. Either realtime patching for the kernel or run the panel process as the main process and use an extremely lightweight server. MQTT with all the lifting on the client?