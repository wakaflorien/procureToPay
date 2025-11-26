"""
Document processing utilities for extracting data from proformas, 
generating POs, and validating receipts.
"""
import json
import re
import logging
from typing import Dict, Any, Optional, Tuple
import pdfplumber
import PyPDF2
from io import BytesIO
import os
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process various document types for the procure-to-pay system"""
    
    @staticmethod
    def _normalize_whitespace(value: Optional[str]) -> str:
        if value is None:
            return ""
        return re.sub(r'\s+', ' ', str(value)).strip()
    
    @staticmethod
    def _clean_entity_name(value: Optional[str]) -> str:
        """Normalize and remove generic placeholders from entity names."""
        cleaned = DocumentProcessor._normalize_whitespace(value)
        if not cleaned:
            return ""
        noise_patterns = [
            r'\b(?:your\s*company|your\s*information)\b',
            r'\b(?:client\s*information|customer\s*name)\b',
            r'\b(?:bill\s*to|billed\s*to|bill\s*from|ship\s*to|sold\s*to|supplier|vendor)\b',
        ]
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            cleaned = DocumentProcessor._normalize_whitespace(cleaned)
        cleaned = cleaned.strip(" -:|,")
        return cleaned
    
    @staticmethod
    def _parse_numeric_value(value: Optional[str]) -> Optional[float]:
        """Convert a loosely formatted numeric string into a float."""
        if value is None:
            return None
        cleaned = re.sub(r'[^\d\-,\.]', '', value)
        if not cleaned:
            return None
        normalized = cleaned.replace(',', '')
        try:
            if normalized in {"", "-", ".", "-."}:
                return None
            return float(normalized)
        except ValueError:
            return None
    
    @staticmethod
    def _parse_line_item(line: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse an invoice line into a structured item (name, quantity, price).
        Returns None when the line does not resemble an item row.
        """
        if not line:
            return None
        candidate = DocumentProcessor._normalize_whitespace(line)
        if not candidate:
            return None
        if not any(ch.isdigit() for ch in candidate):
            return None
        if re.search(r'(?:invoice|total|subtotal|amount\s+due|description|qty|quantity|payment)', candidate, re.IGNORECASE):
            return None
        
        patterns = [
            r'^(?P<name>[A-Za-z][\w\s&\-/,.]+?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s+(?:x\s*)?(?P<unit>[\$€£]?\s*[\d.,]+(?:\s*/[A-Za-z]+)?)\s+(?P<total>[\$€£]?\s*[\d.,]+)$',
            r'^(?P<qty>\d+(?:[.,]\d+)?)\s+(?P<name>[A-Za-z][\w\s&\-/,.]+?)\s+(?:x\s*)?(?P<unit>[\$€£]?\s*[\d.,]+(?:\s*/[A-Za-z]+)?)\s+(?P<total>[\$€£]?\s*[\d.,]+)$',
            r'^(?P<name>[A-Za-z][\w\s&\-/,.]+?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s+(?:x\s*)?(?P<unit>[\$€£]?\s*[\d.,/]+)$',
            r'^(?P<qty>\d+(?:[.,]\d+)?)\s+(?P<name>[A-Za-z][\w\s&\-/,.]+?)\s+(?:x\s*)?(?P<unit>[\$€£]?\s*[\d.,/]+)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, candidate, re.IGNORECASE)
            if not match:
                continue
            groups = match.groupdict()
            qty_val = DocumentProcessor._parse_numeric_value(groups.get('qty'))
            name = DocumentProcessor._normalize_whitespace(groups.get('name'))
            if not qty_val or qty_val <= 0 or not name:
                continue
            unit_val = DocumentProcessor._parse_numeric_value(groups.get('unit'))
            total_val = DocumentProcessor._parse_numeric_value(groups.get('total'))
            price = unit_val
            if price is None and total_val is not None and qty_val:
                price = total_val / qty_val if qty_val else None
            if price is None:
                continue
            return {
                'name': name,
                'quantity': int(round(qty_val)),
                'price': round(price, 2)
            }
        
        return None
    
    @staticmethod
    def _read_file_to_bytesio(file) -> BytesIO:
        """
        Efficiently read file content into BytesIO buffer.
        This avoids multiple seeks and allows multiple reads of the same content.
        """
        buffer = BytesIO()
        
        try:
            # Handle Django file uploads
            if hasattr(file, 'temporary_file_path'):
                # TemporaryUploadedFile - read from disk
                with open(file.temporary_file_path(), 'rb') as f:
                    buffer.write(f.read())
            elif hasattr(file, 'read'):
                # InMemoryUploadedFile or regular file object
                if hasattr(file, 'seek'):
                    file.seek(0)
                buffer.write(file.read())
                if hasattr(file, 'seek'):
                    file.seek(0)  # Reset original file pointer
            else:
                # Try to read directly
                if hasattr(file, 'seek'):
                    file.seek(0)
                buffer.write(file.read())
                if hasattr(file, 'seek'):
                    file.seek(0)
        except Exception as e:
            logger.error(f"Error reading file to buffer: {e}")
            raise
        
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def extract_text_from_image(file) -> str:
        """Extract text from image file (JPG, PNG) using OCR"""
        buffer = None
        try:
            # Read file into buffer for efficient processing
            buffer = DocumentProcessor._read_file_to_bytesio(file)
            
            # Open image from buffer
            image = Image.open(buffer)
            
            # Convert to RGB if necessary (some formats like PNG with transparency)
            if image.mode != 'RGB':
                # Create a white background
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
                else:
                    rgb_image.paste(image)
                image = rgb_image
            
            # Optimize image for OCR (resize if too large, enhance contrast)
            # Large images can slow down OCR significantly
            max_dimension = 2000
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Use pytesseract with optimized configuration
            # PSM 6: Assume a single uniform block of text (good for invoices)
            # OEM 3: Default OCR Engine Mode
            # Try multiple PSM modes for better accuracy
            ocr_configs = [
                '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,$€£:/- ',
                '--psm 11',  # Sparse text
                '--psm 4',   # Single column text
                '--psm 6',   # Single block
            ]
            
            text = ""
            for config in ocr_configs:
                try:
                    text = pytesseract.image_to_string(image, config=config)
                    if text.strip():
                        break
                except Exception:
                    continue
            
            logger.info(f"OCR extracted {len(text)} characters")
            if text.strip():
                logger.debug(f"First 100 chars: {text[:100]}")
            
            return text
        except Exception as e:
            logger.error(f"OCR error: {e}", exc_info=True)
            return ""
        finally:
            if buffer:
                buffer.close()
    
    @staticmethod
    def extract_text_from_pdf(file) -> str:
        """Extract text from PDF file using pdfplumber (preferred) with PyPDF2 fallback."""
        buffer = None
        try:
            buffer = DocumentProcessor._read_file_to_bytesio(file)

            # Primary attempt: pdfplumber
            try:
                buffer.seek(0)
                with pdfplumber.open(buffer) as pdf:
                    text = ""
                    for page_num, page in enumerate(pdf.pages, start=1):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        except Exception as page_exc:
                            logger.warning(f"Error extracting text from page {page_num}: {page_exc}")
                            continue

                    if text.strip():
                        logger.info(
                            f"PDF extracted {len(text)} characters using pdfplumber from {len(pdf.pages)} pages"
                        )
                        return text
            except Exception as exc:
                logger.warning(f"pdfplumber error: {exc}, falling back to PyPDF2")

            # Fallback: PyPDF2
            try:
                buffer.seek(0)
                pdf_reader = PyPDF2.PdfReader(buffer)
                text = ""
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_exc:
                        logger.warning(f"Error extracting text from page {page_num} with PyPDF2: {page_exc}")
                        continue

                if text.strip():
                    logger.info(
                        f"PDF extracted {len(text)} characters using PyPDF2 from {len(pdf_reader.pages)} pages"
                    )
                return text
            except Exception as exc:
                logger.error(f"PyPDF2 error: {exc}", exc_info=True)
                return ""
        except Exception as exc:
            logger.error(f"PDF extraction error: {exc}", exc_info=True)
            return ""
        finally:
            if buffer:
                buffer.close()
    
    @staticmethod
    def _detect_file_type(file) -> Tuple[bool, bool, bool]:
        """
        Detect file type from magic numbers (file header).
        Returns: (is_pdf, is_jpeg, is_png)
        """
        buffer = None
        try:
            buffer = DocumentProcessor._read_file_to_bytesio(file)
            header = buffer.read(16)
            buffer.seek(0)
            
            is_pdf = len(header) >= 4 and header[:4] == b'%PDF'
            is_jpeg = len(header) >= 2 and header[:2] == b'\xff\xd8'
            is_png = len(header) >= 8 and header[:8] == b'\x89PNG\r\n\x1a\n'
            
            return (is_pdf, is_jpeg, is_png)
        except Exception as e:
            logger.warning(f"Error detecting file type: {e}")
            return (False, False, False)
        finally:
            if buffer:
                buffer.close()
    
    @staticmethod
    def extract_text_from_file(file) -> str:
        """Extract text from file (PDF or image) with efficient file type detection"""
        filename = None
        content_type = None
        
        # Get filename if available (Django file uploads have 'name' attribute)
        if hasattr(file, 'name'):
            filename = str(file.name).lower()
        # Check content_type attribute
        if hasattr(file, 'content_type'):
            content_type = str(file.content_type or '').lower()
        
        logger.debug(f"File detection - filename: {filename}, content_type: {content_type}")
        
        # Detect file type from header (magic numbers) - most reliable
        is_pdf, is_jpeg, is_png = DocumentProcessor._detect_file_type(file)
        
        logger.debug(f"Header detection - PDF: {is_pdf}, JPEG: {is_jpeg}, PNG: {is_png}")
        
        # Priority: header detection > filename > content_type > fallback
        if is_pdf:
            logger.info("Detected PDF from header - using PDF extraction")
            text = DocumentProcessor.extract_text_from_pdf(file)
            if text and text.strip():
                return text
            logger.warning("PDF extraction returned no text or failed; attempting OCR fallback.")
            text = DocumentProcessor.extract_text_from_image(file)
            if text and text.strip():
                return text
            return ""
        elif is_jpeg or is_png:
            logger.info(f"Detected image from header (JPEG: {is_jpeg}, PNG: {is_png}) - using OCR")
            return DocumentProcessor.extract_text_from_image(file)
        
        # Fallback to filename extension if header detection failed
        if filename:
            if filename.endswith(('.pdf',)):
                logger.info(f"Detected PDF from filename: {filename} - using PDF extraction")
                text = DocumentProcessor.extract_text_from_pdf(file)
                if text and text.strip():
                    return text
                logger.warning("PDF extraction by filename returned no text; attempting OCR fallback.")
                text = DocumentProcessor.extract_text_from_image(file)
                if text and text.strip():
                    return text
                return ""
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp')):
                logger.info(f"Detected image from filename: {filename} - using OCR")
                return DocumentProcessor.extract_text_from_image(file)
        
        # Fallback to content type
        if content_type:
            if 'pdf' in content_type:
                logger.info(f"Detected PDF from content type: {content_type} - using PDF extraction")
                text = DocumentProcessor.extract_text_from_pdf(file)
                if text and text.strip():
                    return text
                logger.warning("PDF extraction by content-type returned no text; attempting OCR fallback.")
                text = DocumentProcessor.extract_text_from_image(file)
                if text and text.strip():
                    return text
                return ""
            elif 'image' in content_type:
                logger.info(f"Detected image from content type: {content_type} - using OCR")
                return DocumentProcessor.extract_text_from_image(file)
        
        # Last resort: try image OCR first (since PDF errors are more common with images)
        logger.warning("No clear file type detected - trying image OCR first, then PDF")
        text = DocumentProcessor.extract_text_from_image(file)
        if not text or not text.strip():
            logger.info("Image OCR failed or returned no text, trying PDF extraction")
            text = DocumentProcessor.extract_text_from_pdf(file)
        return text
    
    @staticmethod
    def extract_proforma_data(file) -> Dict[str, Any]:
        """Extract data from proforma invoice (PDF or image)"""
        text = DocumentProcessor.extract_text_from_file(file)
        
        if not text or not text.strip():
            return {
                'vendor': "Unknown Vendor",
                'amount': None,
                'items': [],
                'terms': "",
                'extracted_text': "",
                'error': 'No text could be extracted from the document'
            }
        
        lines = text.split('\n')
        
        # Extract vendor information - improved patterns
        vendor = "Unknown Vendor"
        disallowed_vendor_tokens = [
            'invoice', 'proforma', 'date', 'number', 'total', 'amount',
            'due', 'client', 'customer', 'ship', 'shipping', 'bill',
            'billed', 'estimate', 'quote', 'issued', 'payment'
        ]
        vendor_patterns = [
            r'(?:vendor|supplier|company|from|seller|bill\s*from|issued\s*by)[:\s]+([^\n\r]{3,80})',
            r'(?:to|bill\s*to|sold\s*to)[:\s]+([^\n\r]{3,80})',  # Sometimes vendor is in "To" field
            r'^([A-Z][A-Za-z0-9\s&.,\-]{3,60}(?:Inc|LLC|Ltd|Corp|Company|Co\.?|GmbH|S\.A\.?)?)',  # Company name at start
            r'(?:^|\n)([A-Z][A-Za-z0-9\s&.,\-]{3,60}(?:Inc|LLC|Ltd|Corp|Company|Co\.?|GmbH|S\.A\.?)?)\s*(?:\n|$)',  # Company name on its own line
        ]
        
        for pattern in vendor_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            for match in matches:
                vendor_candidate = DocumentProcessor._clean_entity_name(match.group(1))
                if vendor_candidate and len(vendor_candidate) > 2:
                    lowered_candidate = vendor_candidate.lower()
                    if any(token in lowered_candidate for token in disallowed_vendor_tokens):
                        continue
                    vendor = vendor_candidate
                    break
            if vendor != "Unknown Vendor":
                break
        
        if vendor == "Unknown Vendor":
            for line in lines[:20]:
                candidate = DocumentProcessor._clean_entity_name(line)
                if not candidate or len(candidate) < 3:
                    continue
                candidate_lower = candidate.lower()
                if any(token in candidate_lower for token in disallowed_vendor_tokens):
                    continue
                if any(ch.isdigit() for ch in candidate):
                    continue
                vendor = candidate
                break
        
        if not vendor:
            vendor = "Unknown Vendor"
        
        # Extract total amount - improved patterns
        amount = None
        amount_patterns = [
            r'(?:grand\s*total|total\s*amount|amount\s*due|balance\s*due|total\s*payable)[:\s]*[\$€£]?\s*([\d,]+\.?\d{0,2})',
            r'(?:total|amount)[:\s]*[\$€£]?\s*([\d,]+\.?\d{0,2})',
            r'[\$€£]\s*([\d,]+\.?\d{0,2})\s*(?:total|amount|due)',
            r'[\$€£]\s*([\d,]+\.?\d{0,2})(?:\s|$|USD|EUR|GBP)',  # Currency symbol followed by number
            r'(?:USD|EUR|GBP|RWF)\s*([\d,]+\.?\d{0,2})',  # Currency code followed by number
        ]
        
        # Look for amounts in the last part of document (where totals usually are)
        text_lower = text.lower()
        total_section_start = max(
            text_lower.rfind('total'),
            text_lower.rfind('amount'),
            text_lower.rfind('balance'),
            text_lower.rfind('due'),
            len(text) - 800  # Last 800 chars if no keywords found
        )
        total_section = text[total_section_start:]
        
        # Collect all potential amounts
        potential_amounts = []
        for pattern in amount_patterns:
            matches = list(re.finditer(pattern, total_section, re.IGNORECASE))
            for match in matches:
                try:
                    amount_str = match.group(1).replace(',', '').replace(' ', '').strip()
                    amount_value = float(amount_str)
                    if amount_value > 0:  # Sanity check
                        potential_amounts.append(amount_value)
                except (ValueError, IndexError):
                    continue
        
        # Take the largest amount (usually the grand total)
        if potential_amounts:
            amount = max(potential_amounts)
            logger.debug(f"Extracted amount: {amount} from {len(potential_amounts)} potential matches")
        
        # Extract items - improved pattern matching
        items = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Detect items section
            if re.search(r'(?:item|description|product|qty|quantity|price|amount)', line_stripped, re.IGNORECASE):
                continue
            
            # Skip header lines
            if re.search(r'(?:invoice|proforma|date|number|total|subtotal)', line_stripped, re.IGNORECASE) and i < 10:
                continue
            
            normalized_line = DocumentProcessor._normalize_whitespace(line_stripped)
            item_data = DocumentProcessor._parse_line_item(normalized_line)
            if item_data:
                items.append(item_data)
        
        # If no items found with patterns, try to extract from tables
        if not items:
            try:
                buffer = DocumentProcessor._read_file_to_bytesio(file)
                buffer.seek(0)
                with pdfplumber.open(buffer) as pdf:
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        for table in tables:
                            if len(table) > 1:  # Has header and at least one row
                                # Try to identify which columns are quantity, name, price
                                header = [str(cell or '').lower().strip() for cell in table[0]]
                                qty_col = None
                                name_col = None
                                price_col = None
                                
                                for i, h in enumerate(header):
                                    if any(word in h for word in ['qty', 'quantity', 'qty.', 'qty:']):
                                        qty_col = i
                                    elif any(word in h for word in ['item', 'description', 'product', 'name']):
                                        name_col = i
                                    elif any(word in h for word in ['price', 'amount', 'total', 'cost', 'unit']):
                                        price_col = i
                                
                                # If we can't identify columns, use default positions
                                if qty_col is None:
                                    qty_col = 0
                                if name_col is None:
                                    name_col = 1 if len(header) > 1 else 0
                                if price_col is None:
                                    price_col = -1  # Last column
                                
                                for row in table[1:]:  # Skip header
                                    if len(row) > max(qty_col, name_col, abs(price_col) if price_col < 0 else price_col):
                                        try:
                                            qty_val = row[qty_col] if qty_col < len(row) else None
                                            name_val = row[name_col] if name_col < len(row) else None
                                            price_val = row[price_col] if (price_col >= 0 and price_col < len(row)) or (price_col < 0 and len(row) > 0) else None
                                            
                                            if price_col < 0 and len(row) > 0:
                                                price_val = row[-1]
                                            
                                            if qty_val and name_val and price_val:
                                                qty = int(float(str(qty_val).replace(',', '').strip() or 0))
                                                name = str(name_val).strip()
                                                # Clean price string
                                                price_str = str(price_val).replace(',', '').replace('$', '').replace('€', '').replace('£', '').replace('USD', '').replace('EUR', '').replace('GBP', '').strip()
                                                price = float(price_str)
                                                
                                                if qty > 0 and price >= 0 and len(name) > 1:
                                                    items.append({
                                                        'quantity': qty,
                                                        'name': name,
                                                        'price': price
                                                    })
                                        except (ValueError, TypeError, IndexError, AttributeError) as e:
                                            logger.debug(f"Error parsing table row: {e}")
                                            continue
                buffer.close()
            except Exception as e:
                logger.warning(f"Table extraction error: {e}")
                pass
        
        # Extract terms
        terms = ""
        terms_patterns = [
            r'(?:payment\s*terms?|terms?\s*of\s*payment|conditions?)[:\s]+([^\n\r]{5,200})',
            r'(?:net\s*\d+\s*(?:days?)?|due\s*(?:in)?\s*\d+\s*(?:days?))[^\n\r]{0,80}',
            r'(?:due\s*(?:within|in)\s*\d+\s*(?:business\s*)?days[^\n\r]{0,100})',
            r'(?:payment\s+(?:is\s+)?due[^\n\r]{0,120})',
            r'(?:please\s+make\s+the\s+payment[^\n\r]{0,120})',
        ]
        for pattern in terms_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                terms = match.group(1).strip() if match.groups() else match.group(0).strip()
                break
        
        if not terms:
            for line in lines:
                candidate = DocumentProcessor._normalize_whitespace(line)
                if len(candidate) < 25:
                    continue
                if re.search(r'(payment|due|terms)', candidate, re.IGNORECASE):
                    terms = candidate
                    break
        
        return {
            'vendor': vendor,
            'amount': amount,
            'items': items if items else [],
            'terms': terms,
            'extracted_text': text[:1000],  # Store first 1000 chars for reference
        }
    
    @staticmethod
    def generate_purchase_order_data(request, proforma_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate purchase order data from approved request and proforma"""
        po_number = f"PO-{request.id.hex[:8].upper()}-{request.created_at.strftime('%Y%m%d')}"
        
        items = []
        for item in request.items.all():
            items.append({
                'name': item.name,
                'description': item.description,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total': float(item.total_price),
            })
        
        return {
            'po_number': po_number,
            'request_id': str(request.id),
            'vendor': proforma_data.get('vendor', 'Unknown Vendor'),
            'amount': float(request.amount),
            'items': items,
            'terms': proforma_data.get('terms', ''),
            'created_at': request.created_at.isoformat(),
            'approved_by': [
                {
                    'level': 'level_1',
                    'approver': approval.approver.username,
                    'date': approval.created_at.isoformat()
                }
                for approval in request.approvals.filter(action='approved', level='level_1')
            ] + [
                {
                    'level': 'level_2',
                    'approver': approval.approver.username,
                    'date': approval.created_at.isoformat()
                }
                for approval in request.approvals.filter(action='approved', level='level_2')
            ],
        }
    
    @staticmethod
    def validate_receipt(file, purchase_order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate receipt against purchase order (PDF or image)"""
        text = DocumentProcessor.extract_text_from_file(file)
        
        # Extract receipt vendor
        vendor_match = re.search(r'(?:vendor|supplier|company|from|seller):\s*([^\n]+)', text, re.IGNORECASE)
        receipt_vendor = vendor_match.group(1).strip() if vendor_match else "Unknown"
        
        # Extract receipt total
        amount_patterns = [
            r'total[:\s]+[\$€£]?\s*([\d,]+\.?\d*)',
            r'amount[:\s]+[\$€£]?\s*([\d,]+\.?\d*)',
        ]
        receipt_amount = None
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    receipt_amount = float(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # Extract receipt items
        receipt_items = []
        lines = text.split('\n')
        for line in lines:
            item_match = re.search(r'(\d+)\s+([^\d]+?)\s+[\$€£]?\s*(\d+\.?\d*)', line)
            if item_match:
                receipt_items.append({
                    'quantity': int(item_match.group(1)),
                    'name': item_match.group(2).strip(),
                    'price': float(item_match.group(3))
                })
        
        # Validation checks
        po_vendor = purchase_order_data.get('vendor', '')
        po_amount = purchase_order_data.get('amount', 0)
        po_items = purchase_order_data.get('items', [])
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'vendor_match': receipt_vendor.lower() in po_vendor.lower() or po_vendor.lower() in receipt_vendor.lower(),
            'amount_match': abs(receipt_amount - po_amount) < 0.01 if receipt_amount and po_amount else False,
            'items_match': len(receipt_items) == len(po_items),
        }
        
        # Check vendor
        if not validation_result['vendor_match']:
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f"Vendor mismatch: PO vendor '{po_vendor}' vs Receipt vendor '{receipt_vendor}'"
            )
        
        # Check amount
        if receipt_amount and po_amount:
            if abs(receipt_amount - po_amount) > 0.01:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"Amount mismatch: PO amount {po_amount} vs Receipt amount {receipt_amount}"
                )
        
        # Check items count
        if len(receipt_items) != len(po_items):
            validation_result['warnings'].append(
                f"Item count mismatch: PO has {len(po_items)} items, Receipt has {len(receipt_items)} items"
            )
        
        # Store extracted receipt data
        validation_result['receipt_data'] = {
            'vendor': receipt_vendor,
            'amount': receipt_amount,
            'items': receipt_items,
        }
        
        return validation_result

