#include <tunables/global>

profile mcp-browser flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/nameservice>
  #include <abstractions/python>
  #include <abstractions/X>

  # Allow network access
  network inet tcp,
  network inet udp,

  # Access to file system
  /app/** r,
  /app/ r,
  /app/main.py r,
  /home/pwuser/ r,
  /home/pwuser/** rw,
  /tmp/** rw,
  /dev/shm/** rw,
  /usr/lib/** rm,
  /usr/bin/** rm,
  /usr/local/bin/python* ix,
  /usr/local/lib/python*/** rm,
  
  # X11 permissions
  /tmp/.X11-unix/** rw,
  owner /dev/tty* rw,
  owner /proc/*/fd/* r,
  owner /var/tmp/** rw,

  # Browser specific
  deny @{PROC}/* r,
  deny @{PROC}/*/net/if_inet6 r,
  deny @{PROC}/*/stat r,
  owner @{PROC}/*/fd/ r,
  owner @{PROC}/*/task/ r,
  owner @{PROC}/*/status r,
  owner @{PROC}/*/cmdline r,
  owner @{PROC}/*/oom_score_adj rw,
  owner @{PROC}/*/task/** r,
} 