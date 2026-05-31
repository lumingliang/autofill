import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from tests.utils.auth_manager import test_data

class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.session = requests.Session()
    
    def set_token(self, token: str):
        self.token = token
        self.session.headers.update({"token": token})
    
    def clear_token(self):
        self.token = None
        self.session.headers.pop("token", None)
    
    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}/api{endpoint}"
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = self._build_url(endpoint)
        return self.session.get(url, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = self._build_url(endpoint)
        if json:
            return self.session.post(url, json=json)
        return self.session.post(url, data=data)
    
    def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = self._build_url(endpoint)
        return self.session.put(url, json=json)
    
    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = self._build_url(endpoint)
        return self.session.delete(url, params=params)

class ApiResponse:
    def __init__(self, response: requests.Response):
        self.response = response
        self._json: Optional[Dict[str, Any]] = None
    
    @property
    def status_code(self) -> int:
        return self.response.status_code
    
    @property
    def json(self) -> Dict[str, Any]:
        if self._json is None:
            try:
                self._json = self.response.json()
            except ValueError:
                self._json = {}
        return self._json
    
    @property
    def code(self) -> int:
        return self.json.get("code", -1)
    
    @property
    def message(self) -> str:
        return self.json.get("msg", self.json.get("message", ""))
    
    @property
    def data(self) -> Any:
        return self.json.get("data", {})
    
    def is_success(self) -> bool:
        return self.status_code == 200 and self.code == 200
    
    def is_forbidden(self) -> bool:
        return self.status_code == 403 or self.code == 403
    
    def is_error(self) -> bool:
        return not self.is_success()
