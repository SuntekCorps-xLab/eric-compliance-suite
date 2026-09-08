"""Bounded image inputs and direct, public-address-only image downloads."""

import base64
import binascii
import http.client
import ipaddress
import os
import socket
import ssl
import struct
import time
from urllib.parse import urlsplit


MAX_IMAGE_BYTES = 20 * 1024 * 1024


class ImageInputError(ValueError):
    pass


def validate_image(content):
    """Check common image headers, not a full image decoder or safety verdict."""
    if len(content) > MAX_IMAGE_BYTES:
        raise ImageInputError("图片超过 20 MiB 上限。")
    valid = False
    if content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 33:
        valid = (content[8:16] == b"\x00\x00\x00\rIHDR"
                 and all(struct.unpack(">II", content[16:24])))
    elif content.startswith(b"\xff\xd8\xff") and len(content) >= 12:
        valid = content.rstrip().endswith(b"\xff\xd9")
    elif content[:6] in (b"GIF87a", b"GIF89a") and len(content) >= 14:
        valid = all(struct.unpack("<HH", content[6:10])) and content.endswith(b";")
    elif content.startswith(b"RIFF") and len(content) >= 20:
        valid = (content[8:12] == b"WEBP" and content[12:16] in (b"VP8 ", b"VP8L", b"VP8X")
                 and int.from_bytes(content[4:8], "little") + 8 == len(content))
    elif content.startswith(b"BM") and len(content) >= 26:
        valid = int.from_bytes(content[2:6], "little") == len(content)
    if not valid:
        raise ImageInputError("图片内容无效或格式不支持；请检查文件路径，提供 PNG/JPEG/GIF/WebP/BMP 图片。")
    return content


def public_addresses(host, port):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ImageInputError("图片域名没有可用地址。")
    for family, _, _, _, address in addresses:
        if family not in (socket.AF_INET, socket.AF_INET6) or "%" in address[0]:
            raise ImageInputError("图片 URL 必须指向公网地址。")
        ip = ipaddress.ip_address(address[0])
        mapped = getattr(ip, "ipv4_mapped", None)
        if (not ip.is_global or ip.is_multicast or ip.is_reserved
                or (mapped is not None and not mapped.is_global)
                or (ip.version == 6 and ip not in ipaddress.ip_network("2000::/3"))):
            raise ImageInputError("图片 URL 禁止访问内网、回环、链路本地或其他非公网地址。")
        # Transition addresses can hide an IPv4 destination.
        if getattr(ip, "sixtofour", None) is not None or getattr(ip, "teredo", None) is not None:
            raise ImageInputError("图片 URL 不支持 IPv6 隧道地址。")
    return addresses


def public_connection(host, port, secure, address):
    """Connect to the already-validated sockaddr without resolving the host again."""
    family, kind, protocol, _, sockaddr = address
    connection = http.client.HTTPConnection(host, port, timeout=30)
    sock = socket.socket(family, kind, protocol)
    try:
        sock.settimeout(30)
        sock.connect(sockaddr)
        if secure:
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock
        # A dropped connection must not trigger HTTPConnection's unvalidated reconnect.
        connection.auto_open = 0
        return connection
    except BaseException:
        sock.close()
        raise


def download_image(source):
    connection = None
    try:
        if any(ord(char) < 33 or ord(char) == 127 for char in source):
            raise ImageInputError("图片 URL 含空白或控制字符，请使用编码后的直链。")
        url = urlsplit(source)
        if url.scheme not in ("http", "https") or not url.hostname or url.username is not None or url.password is not None:
            raise ImageInputError("图片 URL 必须是无用户名和密码的 HTTP(S) 直链。")
        host = url.hostname.encode("idna").decode("ascii")
        port = url.port or (443 if url.scheme == "https" else 80)
        addresses = public_addresses(host, port)
        deadline = time.monotonic() + 60
        connection = public_connection(host, port, url.scheme == "https", addresses[0])
        path = url.path or "/"
        if url.query:
            path += "?" + url.query
        connection.request("GET", path, headers={"Accept": "image/*", "Accept-Encoding": "identity",
                                                "User-Agent": "ERiC-CLI/1.0"})
        download_socket = connection.sock
        with connection.getresponse() as response:
            if 300 <= response.status < 400:
                raise ImageInputError(f"图片下载 HTTP {response.status}：不跟随重定向，请提供图片直链或本地文件。")
            if response.status != 200:
                raise ImageInputError(f"图片下载 HTTP {response.status}；请检查图片直链。")
            mime = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            if mime and not mime.startswith("image/") and mime != "application/octet-stream":
                raise ImageInputError("图片 URL 返回了非图片 Content-Type；请使用图片直链。")
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise ImageInputError("图片下载不接受压缩传输，请提供图片直链或本地文件。")
            length = response.getheader("Content-Length")
            if length is not None and (int(length) < 0 or int(length) > MAX_IMAGE_BYTES):
                raise ImageInputError("图片超过 20 MiB 上限或 Content-Length 无效。")
            content = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                if download_socket is not None:
                    download_socket.settimeout(min(30, remaining))
                chunk = response.read1(min(65536, MAX_IMAGE_BYTES + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > MAX_IMAGE_BYTES:
                    raise ImageInputError("图片超过 20 MiB 上限。")
            if length is not None and len(content) != int(length):
                raise ImageInputError("图片下载不完整，请检查直链后重试。")
            return validate_image(bytes(content))
    except ImageInputError:
        raise
    except (socket.timeout, TimeoutError) as exc:
        raise ImageInputError("图片下载超时；尚未发送检测请求。") from exc
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # Exception text may contain credentials, signed URLs or response content.
        raise ImageInputError(f"图片下载失败 [{type(exc).__name__}]；请检查 DNS、网络、TLS 或图片直链。") from exc
    finally:
        if connection is not None:
            connection.close()


def load_image(source, offline=False):
    if source.lower().startswith(("http://", "https://")):
        if offline:
            raise ImageInputError("离线模式不下载图片 URL；请先保存图片，再提供本地路径或 base64。")
        content = download_image(source)
    elif os.path.isfile(source):
        with open(source, "rb") as stream:
            content = validate_image(stream.read(MAX_IMAGE_BYTES + 1))
    elif os.path.isdir(source):
        raise ImageInputError("图片路径是目录，请提供图片文件。")
    else:
        if len(source) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
            raise ImageInputError("图片 base64 超过 20 MiB 上限。")
        try:
            content = base64.b64decode(source, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ImageInputError("图片文件不存在或 base64 无效；聊天附件需先保存为可读取的本地图片。") from exc
        content = validate_image(content)
    return base64.b64encode(content).decode("ascii")
