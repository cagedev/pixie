System: Ubuntu Server 20.04
Hardware: Raspberry pi 3 (1GB) with Adafruit RGBHat

## RGBMatrix (hzeller)

## Using `systemd` to run redis in the background


### rq worker

`sudo sysctl status rqworker@1`

● rqworker@1.service - RQ Worker Number 1
     Loaded: loaded (/etc/systemd/system/rqworker@.service; disabled; vendor preset: enabled)
     Active: active (running) since Sat 2020-08-01 19:56:02 UTC; 328ms ago
   Main PID: 6121 (rq)
      Tasks: 1 (limit: 1827)
     CGroup: /system.slice/system-rqworker.slice/rqworker@1.service
             └─6121 /usr/bin/python3 /home/ubuntu/.local/bin/rq worker -c pixie-led.py

Seems fine

`rqinfo`

default      |███████ 7
1 queues, 7 jobs total
0 workers, 1 queues
Updated: 2020-08-01 19:56:58.238937

Why zero workers...?

`sudo ./run_server.sh`

`http://192.168.1.196:5000/pixie/queue?n=10`

Task gets enqueued...

`sudo sysctl status rqworker@1`

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

`redis-cli`
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

OK... so the python file the worker "runs" is it's config file...

```
REDIS_URL = 'redis://localhost:6379/1'
QUEUES = ['high', 'default', 'low']
```
