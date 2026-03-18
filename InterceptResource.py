from mitmproxy import http
from urllib.parse import urlparse
import os

passMethod = {"OPTIONS"}
rootPath = "resources"
allowedHosts = {
    "459aae4bbf.qqyhynprcv.net",
    "common-static-cf.pragmaticplay.net",
}


class RequestFilter:
    def response(self, flow: http.HTTPFlow) -> None:
        method = flow.request.method
        if method in passMethod:
            return

        url = flow.request.pretty_url
        status_code = flow.response.status_code

        if status_code != 200:
            return

        parsed_url = urlparse(url)
        host = parsed_url.netloc

        if host not in allowedHosts:
            return

        path_parts = parsed_url.path.rsplit('/', 1)
        request_path = path_parts[0] if len(path_parts) > 1 else ''
        last_part = path_parts[-1]

        if '?' in last_part:
            last_part = last_part.split('?')[0]

        if '.' in last_part:
            self.save(url, host, request_path, last_part, flow.response.content)

    def save(self, url, host, request_path, last_part, content):
        if not request_path:
            request_path = ""

        dir_path = os.path.join(rootPath, host, request_path.lstrip('/'))
        file_path = os.path.join(dir_path, last_part)

        print(f"[SAVE] {file_path}")

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"  [MKDIR] {dir_path}")

        if not os.path.exists(file_path):
            with open(file_path, 'wb') as f:
                f.write(content)
            print(f"  [OK] {len(content)} bytes")
        else:
            print(f"  [SKIP] 文件已存在")


addons = [RequestFilter()]