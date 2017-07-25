# coding=utf-8
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

effect_analyze = """
--------------------
Info about 'analyze' effect:

bla-bla-bla defencive code.
thousand of bugs inside
Effect class: system defense.

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

node_unavailable = """
--------------------
MountainOfLight/forewall not available

END ----------------
"""

node_firewall = """
--------------------
Node "BlackMirror692/firewall" properties:
Installed program: #7993700
Type: Firewall
DISABLED for: 241 sec
Node effect: trace
Child nodes:
0: traffic_monitor1 (Traffic monitor): #1019788

END ----------------
"""

node_traffic_monitor_1 = """
--------------------
Node "BlackMirror692/traffic_monitor1" properties:
Installed program: #1019788
Type: Traffic monitor
DISABLED for: 572 sec
Node effect: analyze
END ----------------
"""

attack_reply_unavailable = """
executing program #117 from quentin726 target:LadyInRed5000
LadyInRed5000/antivirus2 not available
"""

attack_reply_already_disabled = """
executing program #242 from quentin726 target:BlackMirror692
Error 406: node disabled
"""

attack_reply_success = """
executing program #4851 from quentin726 target:BlackMirror692
Node defence: #2294523
Inevitable effect triggered
Logname:
BlackMirror692 security log updated
attack successfull
"""

attack_reply_failure = """
executing program #980 from quentin726 target:BlackMirror692
Node defence: #43086043
attack failed
Trace:
Proxy level decreased by 1.
BlackMirror692 security log updated
"""

attack_reply_get_data_success = u"""
executing program #20825 from quentin726 target:LadyInRed983
Node defence: #6393275
attack successfull
Data in LadyInRed983/system_information:
--------------------

LadyInRed is ALICE-based cybersystem for Эш (Ash).
ALICE ID: 0000

END ----------------
"""
