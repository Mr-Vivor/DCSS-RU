#!/usr/bin/python3
"""Finish first-time HTTPS provisioning once the purchased domain resolves."""
import os
from pathlib import Path
import socket
import subprocess

BASE = Path('/srv/dcss-ru')
SITE = Path('/etc/nginx/sites-available/dungeoncrawl.ru')
CERT = Path('/etc/letsencrypt/live/dungeoncrawl.ru/fullchain.pem')
DOMAINS = ('dungeoncrawl.ru', 'www.dungeoncrawl.ru')
ADDRESS = '193.104.33.59'


def run(*args):
    subprocess.run(args, check=True)


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    for domain in DOMAINS:
        try:
            addresses = {row[4][0] for row in socket.getaddrinfo(
                domain, 80, socket.AF_INET, socket.SOCK_STREAM)}
        except socket.gaierror:
            print(f'Waiting for DNS: {domain}', flush=True)
            return
        if addresses != {ADDRESS}:
            print(f'Waiting for {domain} to resolve only to {ADDRESS}', flush=True)
            return

    if not CERT.is_file():
        run('certbot', 'certonly', '--non-interactive', '--agree-tos',
            '--webroot', '-w', '/var/www/dungeoncrawl.ru/acme',
            '--cert-name', 'dungeoncrawl.ru',
            '-d', DOMAINS[0], '-d', DOMAINS[1])

    previous = SITE.read_bytes()
    pending = SITE.with_suffix('.pending')
    pending.write_bytes((BASE / 'nginx-https.conf').read_bytes())
    os.replace(pending, SITE)
    try:
        run('nginx', '-t')
        run('systemctl', 'reload', 'nginx')
    except subprocess.CalledProcessError:
        pending.write_bytes(previous)
        os.replace(pending, SITE)
        raise

    # Verify the public SNI route locally without waiting for recursive caches.
    for domain in DOMAINS:
        run('curl', '--fail', '--silent', '--show-error', '--output', '/dev/null',
            '--resolve', f'{domain}:443:127.0.0.1', f'https://{domain}/')
    run('systemctl', 'disable', '--now', 'dcss-ru-https.timer')
    print('HTTPS ready: https://dungeoncrawl.ru/', flush=True)


if __name__ == '__main__':
    main()
