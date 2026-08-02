from vault.verifiers.base_verifier import BaseVerifier
import zipfile
import tempfile
import os
import xml.etree.ElementTree as ET
from vault.verification_status import VerificationStatus, DocumentTypes
from vault.utils import VaultUtils

class AadhaarOfflineEkycVerifier(BaseVerifier):
    def detect(self, file_path):
        return str(file_path).endswith('.zip') or zipfile.is_zipfile(file_path)

    def verify(self, file_path, **kwargs):
        """
        Extracts ZIP using share_code as password, reads XML.
        """
        share_code = kwargs.get('share_code')
        if not share_code:
            return {"status": VerificationStatus.FAILED, "error": "Share code required for Offline Aadhaar ZIP"}
            
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Assuming standard offline e-kyc format: password is share code
                zip_ref.setpassword(str(share_code).encode('utf-8'))
                xml_filename = [f for f in zip_ref.namelist() if f.endswith('.xml')]
                
                if not xml_filename:
                    return {"status": VerificationStatus.FAILED, "error": "No XML found in ZIP"}
                    
                with zip_ref.open(xml_filename[0]) as xml_file:
                    xml_data = xml_file.read()
                    
                return {"status": VerificationStatus.VERIFYING, "xml_data": xml_data}
        except RuntimeError as e:
            if 'password' in str(e).lower() or 'bad password' in str(e).lower():
                return {"status": VerificationStatus.REJECTED, "error": "Invalid Share Code"}
            return {"status": VerificationStatus.FAILED, "error": str(e)}
        except Exception as e:
            return {"status": VerificationStatus.FAILED, "error": str(e)}

    def extract(self, file_path, **kwargs):
        """Extracts fields from the verified XML."""
        xml_data = kwargs.get('xml_data')
        if not xml_data:
            return {}
            
        try:
            root = ET.fromstring(xml_data)
            
            # Find elements handling XML namespaces correctly
            ns = {'uid': 'http://www.uidai.gov.in/offlinePaperlessKYC/2.0'}
            poi = root.find('.//uid:Poi', ns)
            poa = root.find('.//uid:Poa', ns)
            
            if poi is None: 
                # Try without namespace if ns doesn't match
                poi = root.find('.//Poi')
                poa = root.find('.//Poa')
                
            if poi is None:
                return {}
                
            extracted = {
                "name": poi.get('name', ''),
                "dob": VaultUtils.normalize_date(poi.get('dob', '')),
                "gender": poi.get('gender', ''),
                "address": f"{poa.get('house', '')}, {poa.get('street', '')}, {poa.get('dist', '')}, {poa.get('state', '')} - {poa.get('pc', '')}".strip(', '),
                "district": poa.get('dist', ''),
                "state": poa.get('state', ''),
                "pincode": poa.get('pc', ''),
                "reference_id": root.get('referenceId', '')
            }
            return extracted
        except Exception as e:
            print(f"Error parsing Aadhaar XML: {e}")
            return {}

    def validate(self, extracted_data):
        if extracted_data.get('name') and extracted_data.get('dob'):
            return True, VerificationStatus.VERIFIED, 99.0
        return False, VerificationStatus.FAILED, 0.0

    def save(self, metadata, user_id):
        metadata['document_type'] = DocumentTypes.AADHAAR_OFFLINE_ZIP
        metadata['verification_method'] = "OFFLINE_EKYC"
        return metadata
