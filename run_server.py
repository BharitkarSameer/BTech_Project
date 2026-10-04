"""Start the API + PWA on all network interfaces (phone on same Wi-Fi)."""
import socket

import uvicorn


def lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips or ["YOUR_LAN_IP"]


if __name__ == "__main__":
    ips = lan_ips()
    print("Laptop browser:  http://127.0.0.1:8000")
    for ip in ips:
        print(f"Phone (same Wi-Fi): http://{ip}:8000")
    print("If the phone cannot load, allow Python through Windows Firewall,")
    print("or use a phone hotspot — campus Wi-Fi often blocks device-to-device.")
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
