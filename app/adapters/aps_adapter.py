from __future__ import annotations

from dataclasses import dataclass

import app.adapters.aps_client as aps_client

@dataclass
class APSAdapter:
    client_id: str
    client_secret: str

    def convert_rvt_to_ifc(self, rvt_path: str, ifc_path: str) -> None:
        token = aps_client.get_access_token(self.client_id, self.client_secret)
        aps_client.ensure_bucket(token)
        urn = aps_client.upload_file(token, rvt_path)
        aps_client.start_translation(token, urn)
        aps_client.poll_translation(token, urn)
        aps_client.download_ifc(token, urn, ifc_path)
