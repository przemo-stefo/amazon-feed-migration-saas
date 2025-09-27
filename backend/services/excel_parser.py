import pandas as pd
import pyxlsb
from typing import Dict, List, Any, Optional
import os
from loguru import logger

from models.database import FeedType

class ExcelParserService:
    """
    Serwis do parsowania plików Excel/XLSB i wyciągania danych feedów Amazon
    """

    def __init__(self):
        self.supported_extensions = ['.xlsx', '.xlsb', '.xls']

    def parse_file(self, file_path: str, feed_type: FeedType) -> List[Dict[str, Any]]:
        """
        Główna metoda parsowania pliku na podstawie typu feeda
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        try:
            # Wczytanie danych z pliku
            if file_extension == '.xlsb':
                data = self._parse_xlsb(file_path)
            else:
                data = self._parse_excel(file_path)

            # Przetworzenie danych na podstawie typu feeda
            parsed_data = self._process_by_feed_type(data, feed_type)

            logger.info(f"Successfully parsed {len(parsed_data)} items from {file_path}")
            return parsed_data

        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}")
            raise

    def _parse_xlsb(self, file_path: str) -> pd.DataFrame:
        """
        Parsowanie pliku XLSB
        """
        try:
            # Próba automatycznego wykrycia arkusza z danymi
            with pyxlsb.open_workbook(file_path) as wb:
                sheet_names = wb.get_sheet_names()
                logger.info(f"Available sheets: {sheet_names}")

                # Szukamy arkusza z największą ilością danych
                best_sheet = None
                max_rows = 0

                for sheet_name in sheet_names:
                    try:
                        df_temp = pd.read_excel(file_path, sheet_name=sheet_name, engine='pyxlsb')
                        if len(df_temp) > max_rows:
                            max_rows = len(df_temp)
                            best_sheet = sheet_name
                    except:
                        continue

                if best_sheet:
                    df = pd.read_excel(file_path, sheet_name=best_sheet, engine='pyxlsb')
                else:
                    # Fallback na pierwszy arkusz
                    df = pd.read_excel(file_path, engine='pyxlsb')

            return df

        except Exception as e:
            logger.error(f"Error parsing XLSB file: {str(e)}")
            raise

    def _parse_excel(self, file_path: str) -> pd.DataFrame:
        """
        Parsowanie pliku Excel (.xlsx, .xls)
        """
        try:
            # Próba automatycznego wykrycia arkusza z danymi
            xl_file = pd.ExcelFile(file_path)
            sheet_names = xl_file.sheet_names
            logger.info(f"Available sheets: {sheet_names}")

            # Szukamy arkusza z największą ilością danych
            best_sheet = None
            max_rows = 0

            for sheet_name in sheet_names:
                try:
                    df_temp = pd.read_excel(file_path, sheet_name=sheet_name)
                    if len(df_temp) > max_rows:
                        max_rows = len(df_temp)
                        best_sheet = sheet_name
                except:
                    continue

            if best_sheet:
                df = pd.read_excel(file_path, sheet_name=best_sheet)
            else:
                # Fallback na pierwszy arkusz
                df = pd.read_excel(file_path)

            return df

        except Exception as e:
            logger.error(f"Error parsing Excel file: {str(e)}")
            raise

    def _process_by_feed_type(self, df: pd.DataFrame, feed_type: FeedType) -> List[Dict[str, Any]]:
        """
        Przetwarzanie danych na podstawie typu feeda
        """
        # Normalizacja nazw kolumn (lowercase, bez spacji)
        df.columns = [str(col).lower().strip().replace(' ', '_') for col in df.columns]

        if feed_type == FeedType.INVENTORY:
            return self._process_inventory_feed(df)
        elif feed_type == FeedType.PRICING:
            return self._process_pricing_feed(df)
        elif feed_type == FeedType.LISTINGS:
            return self._process_listings_feed(df)
        elif feed_type == FeedType.IMAGES:
            return self._process_images_feed(df)
        else:
            raise ValueError(f"Unsupported feed type: {feed_type}")

    def _process_inventory_feed(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Przetwarzanie feeda inventory
        Oczekiwane kolumny: SKU, Quantity, Fulfillment_Center_ID
        """
        required_columns = ['sku']
        optional_columns = ['quantity', 'fulfillment_center_id', 'available']

        # Sprawdzenie obecności wymaganych kolumn
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            # Próba mapowania popularnych nazw kolumn
            column_mapping = self._get_column_mapping(df.columns)
            df = df.rename(columns=column_mapping)

            # Ponowne sprawdzenie
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns for inventory feed: {missing_columns}")

        # Konwersja do listy słowników
        records = []
        for _, row in df.iterrows():
            record = {
                'sku': str(row.get('sku', '')).strip(),
                'quantity': int(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0,
                'fulfillment_center_id': str(row.get('fulfillment_center_id', 'DEFAULT')),
                'original_data': row.to_dict()
            }

            # Filtrowanie pustych SKU
            if record['sku']:
                records.append(record)

        return records

    def _process_pricing_feed(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Przetwarzanie feeda pricing
        Oczekiwane kolumny: SKU, Price, Currency
        """
        required_columns = ['sku']
        optional_columns = ['price', 'currency', 'sale_price', 'sale_start_date', 'sale_end_date']

        # Sprawdzenie i mapowanie kolumn
        column_mapping = self._get_column_mapping(df.columns)
        df = df.rename(columns=column_mapping)

        records = []
        for _, row in df.iterrows():
            record = {
                'sku': str(row.get('sku', '')).strip(),
                'price': float(row.get('price', 0)) if pd.notna(row.get('price')) else 0,
                'currency': str(row.get('currency', 'USD')),
                'sale_price': float(row.get('sale_price')) if pd.notna(row.get('sale_price')) else None,
                'original_data': row.to_dict()
            }

            if record['sku']:
                records.append(record)

        return records

    def _process_listings_feed(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Przetwarzanie feeda listings (produkty)
        """
        column_mapping = self._get_column_mapping(df.columns)
        df = df.rename(columns=column_mapping)

        records = []
        for _, row in df.iterrows():
            record = {
                'sku': str(row.get('sku', '')).strip(),
                'title': str(row.get('title', '')),
                'description': str(row.get('description', '')),
                'brand': str(row.get('brand', '')),
                'category': str(row.get('category', '')),
                'price': float(row.get('price', 0)) if pd.notna(row.get('price')) else 0,
                'images': str(row.get('images', '')).split(',') if row.get('images') else [],
                'original_data': row.to_dict()
            }

            if record['sku']:
                records.append(record)

        return records

    def _process_images_feed(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Przetwarzanie feeda images
        """
        column_mapping = self._get_column_mapping(df.columns)
        df = df.rename(columns=column_mapping)

        records = []
        for _, row in df.iterrows():
            record = {
                'sku': str(row.get('sku', '')).strip(),
                'main_image': str(row.get('main_image', '')),
                'additional_images': str(row.get('additional_images', '')).split(',') if row.get('additional_images') else [],
                'original_data': row.to_dict()
            }

            if record['sku']:
                records.append(record)

        return records

    def _get_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """
        Mapowanie popularnych nazw kolumn na standardowe nazwy
        """
        mapping = {}

        for col in columns:
            col_lower = col.lower().strip()

            # Mapowanie SKU
            if any(keyword in col_lower for keyword in ['sku', 'seller_sku', 'msku', 'merchant_sku']):
                mapping[col] = 'sku'

            # Mapowanie quantity
            elif any(keyword in col_lower for keyword in ['quantity', 'qty', 'stock', 'inventory']):
                mapping[col] = 'quantity'

            # Mapowanie price
            elif any(keyword in col_lower for keyword in ['price', 'cost', 'amount']):
                mapping[col] = 'price'

            # Mapowanie title
            elif any(keyword in col_lower for keyword in ['title', 'name', 'product_name']):
                mapping[col] = 'title'

            # Mapowanie description
            elif any(keyword in col_lower for keyword in ['description', 'desc', 'details']):
                mapping[col] = 'description'

            # Mapowanie brand
            elif any(keyword in col_lower for keyword in ['brand', 'manufacturer', 'make']):
                mapping[col] = 'brand'

            # Mapowanie images
            elif any(keyword in col_lower for keyword in ['image', 'photo', 'picture']):
                if 'main' in col_lower or 'primary' in col_lower:
                    mapping[col] = 'main_image'
                else:
                    mapping[col] = 'additional_images'

        return mapping

    def validate_data(self, data: List[Dict[str, Any]], feed_type: FeedType) -> Dict[str, Any]:
        """
        Walidacja sparsowanych danych
        """
        total_items = len(data)
        valid_items = 0
        errors = []

        for i, item in enumerate(data):
            item_errors = []

            # Podstawowa walidacja SKU
            if not item.get('sku'):
                item_errors.append("Missing SKU")

            # Walidacja specyficzna dla typu feeda
            if feed_type == FeedType.INVENTORY:
                if item.get('quantity', 0) < 0:
                    item_errors.append("Negative quantity")

            elif feed_type == FeedType.PRICING:
                if item.get('price', 0) <= 0:
                    item_errors.append("Invalid price")

            elif feed_type == FeedType.LISTINGS:
                if not item.get('title'):
                    item_errors.append("Missing title")

            if not item_errors:
                valid_items += 1
            else:
                errors.append({
                    'row': i + 1,
                    'sku': item.get('sku', 'Unknown'),
                    'errors': item_errors
                })

        return {
            'total_items': total_items,
            'valid_items': valid_items,
            'invalid_items': total_items - valid_items,
            'errors': errors[:50]  # Ograniczenie do 50 pierwszych błędów
        }