# AppArmor profile for MCP Browser
#include <tunables/global>

profile mcp-browser flags=(attach_disconnected) {
    #include <abstractions/base>
    #include <abstractions/python>
    #include <abstractions/nameservice>
    #include <abstractions/openssl>

    # Basic capabilities
    capability net_bind_service,
    capability setuid,
    capability setgid,
    capability sys_chroot,
    capability sys_admin,

    # Allow network access
    network inet stream,
    network inet6 stream,
    network unix stream,

    # Allow process operations
    ptrace (read) peer=@{profile_name},
    signal (receive) peer=@{profile_name},

    # Allow file operations
    /usr/bin/python3* ix,
    /usr/local/bin/python3* ix,
    /usr/lib/python3/** r,
    /usr/local/lib/python3/** r,
    
    # Allow rate limiting storage
    owner /tmp/mcp-browser-rate-limit/ rw,
    owner /tmp/mcp-browser-rate-limit/** rwk,
    
    # Allow browser operations
    owner @{PROC}/@{pid}/fd/ r,
    owner @{PROC}/@{pid}/task/@{pid}/stat r,
    owner @{PROC}/@{pid}/stat r,
    owner @{PROC}/@{pid}/cmdline r,
    owner @{PROC}/@{pid}/status r,
    owner @{PROC}/@{pid}/mem r,
    owner @{PROC}/@{pid}/auxv r,
    
    # Allow system metrics for rate limiting
    @{PROC}/loadavg r,
    @{PROC}/stat r,
    @{PROC}/meminfo r,
    @{PROC}/cpuinfo r,
    
    # Allow browser process monitoring
    @{PROC}/*/{stat,status,cmdline} r,
    
    # Allow X11 display
    /tmp/.X11-unix/* rw,
    
    # Allow SSL certificates
    /etc/ssl/certs/** r,
    /usr/share/ca-certificates/** r,
    
    # Allow application paths
    /app/** r,
    /app/src/** r,
    /app/static/** r,
    owner /app/output/** rw,
    
    # Allow temporary files
    owner /tmp/** rwk,
    
    # Allow log files
    owner /var/log/mcp-browser/ rw,
    owner /var/log/mcp-browser/** rw,
    
    # Allow shared memory
    owner /{,var/}run/shm/** rwk,
    
    # Allow browser sandbox
    owner /dev/shm/** rwk,
    
    deny @{PROC}/sys/kernel/yama/ptrace_scope w,
    deny @{PROC}/sys/kernel/suid_dumpable w,
    deny @{PROC}/sysrq-trigger w,
    deny @{PROC}/kcore r,
} 