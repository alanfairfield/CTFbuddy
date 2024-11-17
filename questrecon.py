import os
import argparse
import nmap
from colorama import Fore, Back, Style
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


# Function to print ASCII art 
def print_ascii_art():
    ascii_art = (Fore.YELLOW + Back.RED + Style.BRIGHT + r'''
+~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-+                                                                   
|     (                           )   )\ )                               |
|   ( )\      (      (         ( /(  (()/(     (                         |
|   )((_)    ))\    ))\   (    )\())  /(_))   ))\    (     (     (       |
|  ((_)_    /((_)  /((_)  )\  (_))/  (_))    /((_)   )\    )\    )\ )    |
|   / _ \  (_))(  (_))   ((_) | |_   | _ \  (_))    ((_)  ((_)  _(_/(    |
|  | (_) | | || | / -_)  (_-< |  _|  |   /  / -_)  / _|  / _ \ | ' \))   |
|   \__\_\  \_,_| \___|  /__/  \__|  |_|_\  \___|  \__|  \___/ |_||_|    |
|                                                                        |
+~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-+                                                                        
''' + Style.RESET_ALL)

    print(ascii_art)
    print(Fore.WHITE + Back.MAGENTA + Style.BRIGHT + "\nThe quieter you become, the more you can hear.\n" + Style.RESET_ALL + Style.BRIGHT + '\n...\n')

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--target', help='Specify the target IP address, CIDR range, or hostname')
parser.add_argument('-H', '--hosts', help='Specify the path to a file containing host(s) separated by one or more spaces, tabs, or newlines')
parser.add_argument('-o', '--out', help='Specify the directory name path to output the results. E.g., ~/Pentests/Client1')
args = parser.parse_args()

# Variables from arguments
target = args.target
hosts = args.hosts
output_dir = args.out

# Create output directory if it doesn't already exist
def create_output_dir():
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(f'{output_dir}/results')
            print(f"[+] Output directory created: {output_dir}/results")
        except Exception as e:
            print(f"[-] Something went wrong with the creation of the output directory! Error: {e}")

# UDP Scan
def udp_nmap(target):
    nm = nmap.PortScanner()
    try:
        target_dir = Path(output_dir) / "results" / target
        target_dir.mkdir(parents=True, exist_ok=True)

        print(Fore.GREEN + f"[+] Running Quick UDP scan on {target}..." + Style.RESET_ALL)
        nm.scan(target, arguments=f"-sU -F -oN {target_dir}/quick_nmap_udp")
        udp_ports = nm[target]['udp'].keys() if 'udp' in nm[target] else []
        print(f"[+] UDP Ports open on {target}: {list(udp_ports)}")
        return set(udp_ports)
    except Exception as e:
        print(f"[-] An error occurred during scanning: {e}")
        return set()

# TCP Scan
def tcp_nmap(target):
    nm = nmap.PortScanner()
    try:
        target_dir = Path(output_dir) / "results" / target
        target_dir.mkdir(parents=True, exist_ok=True)

        print(Fore.GREEN + f"[+] Running Full TCP scan on {target} to determine which ports are open..." + Style.RESET_ALL)
        nm.scan(target, arguments=f"-p- -oN {target_dir}/quick_nmap_tcp")
        tcp_ports = nm[target]['tcp'].keys() if 'tcp' in nm[target] else []
        print(f"[+] TCP Ports open on {target}: {list(tcp_ports)}")
        return set(tcp_ports)
    except Exception as e:
        print(f"[-] An error occurred during scanning: {e}")
        return set()

# TCP Service Scan
def tcp_service(target, port):
    nm = nmap.PortScanner()
    try:
        print(Fore.WHITE + Back.BLACK + Style.BRIGHT + f"[+] Service Scanning TCP Port {port} on target {target}" + Style.RESET_ALL)
        target_dir = Path(output_dir) / "results" / target / str(port)
        target_dir.mkdir(parents=True, exist_ok=True)
        nm.scan(target, arguments=f"-p{port} -sV -sC -oN {target_dir}/tcp{port}_service_scan")
        print(Fore.GREEN + f"[+] Service scan completed for TCP port {port} on {target}" + Style.RESET_ALL)
    except Exception as e:
        print(f"[-] TCP service scan error for {target}:{port}: {e}")

# UDP Service Scan
def udp_service(target, port):
    nm = nmap.PortScanner()
    try:
        print(Fore.WHITE + Back.BLACK + Style.BRIGHT + f"[+] Service Scanning UDP Port {port} on target {target}" + Style.RESET_ALL)
        target_dir = Path(output_dir) / "results" / target / str(port)
        target_dir.mkdir(parents=True, exist_ok=True)
        nm.scan(target, arguments=f"-p{port} -sV -sC -sU -oN {target_dir}/udp{port}_service_scan")
        print(Fore.GREEN + f"[+] Service scan completed for UDP port {port} on {target}" + Style.RESET_ALL)
    except Exception as e:
        print(f"[-] UDP service scan error for {target}:{port}: {e}")

# Handle multiple targets from a file
def scan_multiple_hosts(hosts):
    """Scan multiple targets from a host file using threading for concurrency."""
    with open(hosts, 'r') as file:
        host_list = [line.strip() for line in file if line.strip()]

    with ThreadPoolExecutor() as executor:
        future_to_host = {}

        # Submit quick TCP and UDP scans for each host
        for host in host_list:
            print(Fore.CYAN + f"[+] Starting scans for host: {host}" + Style.RESET_ALL)
            future_to_host[executor.submit(tcp_nmap, host)] = (host, 'tcp')
            future_to_host[executor.submit(udp_nmap, host)] = (host, 'udp')

        # Process quick scan results and schedule service scans
        for future in as_completed(future_to_host):
            host, scan_type = future_to_host[future]
            try:
                ports = future.result()
                if scan_type == 'tcp':
                    print(Fore.GREEN + f"[+] TCP Ports open on {host}: {list(ports)}" + Style.RESET_ALL)
                    for port in ports:
                        executor.submit(tcp_service, host, port)
                elif scan_type == 'udp':
                    print(Fore.GREEN + f"[+] UDP Ports open on {host}: {list(ports)}" + Style.RESET_ALL)
                    for port in ports:
                        executor.submit(udp_service, host, port)
            except Exception as e:
                print(f"[-] Error processing {scan_type.upper()} scan for {host}: {e}")

# Main
def main():
    print_ascii_art()
    create_output_dir()

    if target:
        with ThreadPoolExecutor() as executor:
            futures_tcp = executor.submit(tcp_nmap, target)
            futures_udp = executor.submit(udp_nmap, target)

            for future in as_completed([futures_tcp, futures_udp]):
                if future == futures_tcp:
                    tcp_ports = future.result()
                    for port in tcp_ports:
                        executor.submit(tcp_service, target, port)
                elif future == futures_udp:
                    udp_ports = future.result()
                    for port in udp_ports:
                        executor.submit(udp_service, target, port)
    elif hosts:
        scan_multiple_hosts(hosts)
    else:
        print("[-] Please specify a target using '-t' or provide a hosts file using '-H'")

# Run the program
if __name__ == "__main__":
    main()
