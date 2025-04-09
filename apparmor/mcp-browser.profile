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

    # Network access controls
    network inet stream,
    network inet6 stream,
    network unix stream,
    
    # Deny raw socket access
    deny network raw,
    
    # Allow specific ports
    network inet tcp port 8000,
    network inet tcp port 7665,
    
    # Deny ICMP
    deny network inet icmp,
    deny network inet6 icmp,
    
    # Process operations
    ptrace (read) peer=@{profile_name},
    signal (receive) peer=@{profile_name},

    # File operations
    /usr/bin/python3* ix,
    /usr/local/bin/python3* ix,
    /usr/lib/python3/** r,
    /usr/local/lib/python3/** r,
    
    # Rate limiting storage
    owner /tmp/mcp-browser-rate-limit/ rw,
    owner /tmp/mcp-browser-rate-limit/** rwk,
    
    # Browser operations
    owner @{PROC}/@{pid}/fd/ r,
    owner @{PROC}/@{pid}/task/@{pid}/stat r,
    owner @{PROC}/@{pid}/stat r,
    owner @{PROC}/@{pid}/cmdline r,
    owner @{PROC}/@{pid}/status r,
    owner @{PROC}/@{pid}/mem r,
    owner @{PROC}/@{pid}/auxv r,
    
    # System metrics
    @{PROC}/loadavg r,
    @{PROC}/stat r,
    @{PROC}/meminfo r,
    @{PROC}/cpuinfo r,
    
    # Browser process monitoring
    @{PROC}/*/{stat,status,cmdline} r,
    
    # X11 display
    /tmp/.X11-unix/* rw,
    
    # SSL certificates
    /etc/ssl/certs/** r,
    /usr/share/ca-certificates/** r,
    
    # Application paths
    /app/** r,
    /app/src/** r,
    /app/static/** r,
    owner /app/output/** rw,
    
    # Temporary files
    owner /tmp/** rwk,
    
    # Log files
    owner /var/log/mcp-browser/ rw,
    owner /var/log/mcp-browser/** rw,
    
    # Shared memory
    owner /{,var/}run/shm/** rwk,
    
    # Browser sandbox
    owner /dev/shm/** rwk,
    
    # Security denials
    deny @{PROC}/sys/kernel/yama/ptrace_scope w,
    deny @{PROC}/sys/kernel/suid_dumpable w,
    deny @{PROC}/sysrq-trigger w,
    deny @{PROC}/kcore r,
    
    # Network security
    deny network inet raw,
    deny network inet6 raw,
    deny network packet,
    deny network netlink,
    
    # Additional security
    deny @{PROC}/sys/net/ipv4/conf/*/accept_redirects w,
    deny @{PROC}/sys/net/ipv4/conf/*/send_redirects w,
    deny @{PROC}/sys/net/ipv4/ip_forward w,
    deny @{PROC}/sys/net/ipv6/conf/*/accept_redirects w,
    deny @{PROC}/sys/net/ipv6/conf/*/send_redirects w,
    deny @{PROC}/sys/net/ipv6/ip_forward w,
} 