import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class LogParser:
    BRACKET_REGEX = re.compile(
        r'^\s*(?:\[?(?P<timestamp>\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\]?)?\s*'
        r'(?:\[?(?P<level>FATAL|CRITICAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\]?)?\s*'
        r'(?:\[?(?P<service>[a-zA-Z0-9_\-\.]+)\]?)?\s*[:-]?\s*(?P<message>.*)$',
        re.IGNORECASE
    )

    ISO_PREFIX = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
        r'(?P<level>[A-Z]+)\s+(?:\[(?P<service>[^\]]+)\]\s+)?(?P<message>.*)$'
    )

    @classmethod
    def parse_line(cls, raw_line: str, default_service: str = 'default-svc') -> Optional[Dict[str, Any]]:
        line = raw_line.strip()
        if not line:
            return None

        # 1. JSON
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                timestamp_raw = data.get('timestamp') or data.get('time') or data.get('@timestamp')
                level = str(data.get('level') or data.get('severity') or data.get('log_level') or 'INFO').upper()
                service = str(data.get('service') or data.get('app') or data.get('svc') or default_service)
                message = str(data.get('message') or data.get('msg') or data.get('log') or line)
                return {
                    'timestamp': cls._parse_timestamp(timestamp_raw),
                    'level': cls._normalize_level(level),
                    'service': service,
                    'message': message,
                    'raw': line,
                    'attributes': {k: v for k, v in data.items() if k not in ('timestamp', 'time', '@timestamp', 'level', 'severity', 'message', 'msg')}
                }
            except Exception:
                pass

        # 2. ISO Prefix
        match = cls.ISO_PREFIX.match(line)
        if match:
            gd = match.groupdict()
            return {
                'timestamp': cls._parse_timestamp(gd.get('timestamp')),
                'level': cls._normalize_level(gd.get('level')),
                'service': gd.get('service') or default_service,
                'message': gd.get('message', ''),
                'raw': line,
                'attributes': {}
            }

        # 3. Bracketed format
        match = cls.BRACKET_REGEX.match(line)
        if match:
            gd = match.groupdict()
            return {
                'timestamp': cls._parse_timestamp(gd.get('timestamp')),
                'level': cls._normalize_level(gd.get('level')),
                'service': gd.get('service') or default_service,
                'message': gd.get('message') or line,
                'raw': line,
                'attributes': {}
            }

        # 4. Fallback Plaintext
        return {
            'timestamp': datetime.now(timezone.utc),
            'level': 'INFO',
            'service': default_service,
            'message': line,
            'raw': line,
            'attributes': {}
        }

    @staticmethod
    def _normalize_level(level: Optional[str]) -> str:
        if not level:
            return 'INFO'
        lvl = level.strip().upper()
        if lvl in ('FATAL', 'CRITICAL'):
            return 'CRITICAL'
        if lvl in ('ERROR', 'ERR'):
            return 'ERROR'
        if lvl in ('WARN', 'WARNING'):
            return 'WARN'
        if lvl in ('DEBUG', 'TRACE'):
            return 'DEBUG'
        return 'INFO'

    @staticmethod
    def _parse_timestamp(ts_str: Optional[str]) -> datetime:
        if not ts_str:
            return datetime.now(timezone.utc)
        try:
            clean = ts_str.replace('Z', '+00:00')
            return datetime.fromisoformat(clean)
        except Exception:
            return datetime.now(timezone.utc)
