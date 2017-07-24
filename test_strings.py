hacker_proxy_not_set = """
--------------------
quentin726 status:
Current target: MountainOfLight
Current administrating system: none
Warning: proxy not available
END ----------------
"""
hacker_first = """
--------------------
quentin726 status:
Current target: not set
Current administrating system: none
Proxy level: 6
Current proxy address: kenguru7448@sydney
END ----------------
"""

effect_trace = """
--------------------
Info about 'trace' effect:


This effect traces your connection to origin point.
Effectively this decrease your proxy level by 1.
After that it Logs attacker current address (login) to the system log.
If attacker still have proxy, his proxy address will be logged instead.
Effect class: system defense.

END ----------------
"""

effect_get_data = """
--------------------
Info about 'read_data' effect:


This effect silently reads data stored in the target node and delivers it to hacker.
This effect normally leaves no traces in system logs if successful.
Effect class: worm.



END ----------------
"""

effect_disable = """
--------------------
Info about 'disable' effect:

bla-bla-bla malicious code.
thousand of bugs inside
Effect class: virus.

END ----------------
"""

command_attack_disable = """
--------------------
#3675 programm info:
Effect: disable
Allowed node types:
 -Firewall
 -Antivirus
 -VPN
 -Brandmauer
 -Router
 -Traffic monitor
 -Cyptographic system
Duration: 600sec.
END ----------------
"""

command_defence = """
--------------------
#432225 programm info:
Effect: trace
Inevitable effect: analyze
Allowed node types:
 -Firewall
 -Antivirus
 -VPN
 -Brandmauer
 -Router
 -Traffic monitor
 -Cyptographic system
END ----------------
"""

node_disabled = """
--------------------
Node "BlackMirror692/VPN3" properties:
Installed program: #7993700
Type: VPN
DISABLED for: 241 sec
Node effect: trace
Child nodes:
0: traffic_monitor1 (Traffic monitor): #1019788
1: brandmauer3 (Brandmauer): #2294523

END ----------------
"""

node_enabled = """
--------------------
Node "BlackMirror692/firewall" properties:
Installed program: #6449300
Type: Firewall
END ----------------
"""

node_with_effect = """
--------------------
Node "BlackMirror692/VPN3" properties:
Installed program: #7993700
Type: VPN
DISABLED for: 517 sec
Node effect: trace
Child nodes:
0: traffic_monitor1 (Traffic monitor): #1019788 DISABLED
1: brandmauer3 (Brandmauer): #2294523 DISABLED

END ----------------
"""

node_encrypted = """
--------------------
Node "ManInBlack/cryptocore1" properties:
Installed program: *encrypted*
Type: Cyptographic system
DISABLED for: 117 sec
Child nodes:
0: antivirus7 (Antivirus): #686575175 DISABLED
1: VPN2 (VPN): #164328164
END ----------------
"""

node_short = """
VPN3 (VPN): #5887791   Child nodes:[cryptocore1, antivirus1, traffic_monitor1]
"""