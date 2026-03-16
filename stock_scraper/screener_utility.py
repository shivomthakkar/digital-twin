"""
Screener.in Utility Module
Shared utilities for fetching data from Screener.in

No CrewAI dependencies — pure requests + BeautifulSoup.
"""

import re
import requests
from typing import Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
# from pathlib import Path


class ScreenerFetcher:
    """Utility class for interacting with Screener.in"""

    BASE_URL = "https://www.screener.in"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self):
        # self.data_dir = Path(data_dir)
        # self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ------------------------------------------------------------------
    # Search & page fetch
    # ------------------------------------------------------------------

    def search_company(self, query: str) -> Optional[str]:
        """
        Search Screener.in for a company by symbol or name.

        Screener's search API handles both:
          - Symbols  → 'TCS', 'INFY', 'RELIANCE'
          - Names    → 'Tata Consultancy', 'Infosys Ltd'

        Returns:
            URL path like '/company/TCS/' or None if not found.
        """
        search_url = f"{self.BASE_URL}/api/company/search/"
        params = {"q": query}
        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            results = response.json()
            if not results:
                return None
            return results[0].get("url")
        except Exception:
            return None

    def get_company_page(self, company_url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse the company page.

        Returns:
            BeautifulSoup object or None on failure.
        """
        full_url = urljoin(self.BASE_URL, company_url)
        try:
            response = self.session.get(full_url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Financial data extraction
    # ------------------------------------------------------------------

    def extract_financial_data(self, soup: BeautifulSoup) -> Dict:
        """
        Extract core financial ratios and metrics from a company page.

        Returns:
            Dictionary of financial metrics; always has 'company_name' key.
        """
        financial_data: Dict = {"company_name": ""}

        def add_if_exists(key: str, value: str):
            if value and str(value).strip():
                financial_data[key] = str(value).strip()

        def extract_number(text: str) -> str:
            match = re.search(r"[\d,]+\.?\d*", text)
            return match.group(0).replace(",", "") if match else ""

        metrics_to_extract = [
            # Market & price
            (["market cap"], "market_cap"),
            (["current price"], "current_price"),
            (["book value"], "book_value"),
            (["face value"], "face_value"),
            (["dividend yield"], "dividend_yield"),
            (["52w high", "52 week high"], "52_week_high"),
            (["52w low", "52 week low"], "52_week_low"),
            (["high / low"], "high_low"),
            # Valuation
            (["stock p/e", "stock pe"], "stock_pe"),
            (["p/e ratio", "pe ratio", "price to earnings"], "pe_ratio"),
            (["p/b ratio", "pb ratio", "price to book"], "pb_ratio"),
            (["price to sales", "p/s ratio"], "price_to_sales"),
            (["ev/ebitda", "ev / ebitda"], "ev_to_ebitda"),
            (["ev/sales", "ev / sales"], "ev_to_sales"),
            (["peg ratio"], "peg_ratio"),
            # Profitability
            (["roe", "return on equity"], "roe"),
            (["roce", "return on capital employed"], "roce"),
            (["roa", "return on assets"], "roa"),
            (["opm", "operating profit margin", "operating margin"], "opm"),
            (["npm", "net profit margin"], "npm"),
            (["ebitda margin"], "ebitda_margin"),
            # Health
            (["debt to equity", "d/e ratio", "debt / equity"], "debt_to_equity"),
            (["debt"], "debt"),
            (["current ratio"], "current_ratio"),
            (["quick ratio"], "quick_ratio"),
            (["interest coverage"], "interest_coverage"),
            (["asset turnover"], "asset_turnover"),
            # Growth
            (["sales growth 3", "sales growth 3yr", "sales cagr 3"], "sales_growth_3yr"),
            (["sales growth 5", "sales growth 5yr", "sales cagr 5"], "sales_growth_5yr"),
            (["sales growth ttm"], "sales_growth_ttm"),
            (["sales growth"], "sales_growth"),
            (["profit growth 3", "profit growth 3yr"], "profit_growth_3yr"),
            (["profit growth 5", "profit growth 5yr"], "profit_growth_5yr"),
            (["profit growth ttm"], "profit_growth_ttm"),
            (["profit growth"], "profit_growth"),
            (["eps growth 3", "eps growth 3yr"], "eps_growth_3yr"),
            (["eps growth 5", "eps growth 5yr"], "eps_growth_5yr"),
            (["eps growth"], "eps_growth"),
            (["revenue growth"], "revenue_growth"),
            # Per share
            (["eps ttm"], "eps_ttm"),
            (["eps", "earnings per share"], "eps"),
            (["cash eps"], "cash_eps"),
            (["book value per share", "bvps"], "book_value_per_share"),
            (["sales per share"], "sales_per_share"),
            (["dividend per share", "dps"], "dividend_per_share"),
            # Shareholding
            (["promoter holding", "promoters"], "promoter_holding"),
            (["fii holding", "fii"], "fii_holding"),
            (["dii holding", "dii"], "dii_holding"),
            (["public holding"], "public_holding"),
            (["pledge", "pledged shares"], "pledge_percentage"),
            # Technical
            (["rsi", "relative strength index"], "rsi"),
            # Other
            (["enterprise value"], "enterprise_value"),
            (["total shares", "outstanding shares"], "total_shares"),
            (["market cap rank"], "market_cap_rank"),
        ]

        # Company name
        name_tag = soup.find("h1", class_=re.compile("company|name"))
        if not name_tag:
            name_tag = soup.find("h1")
        if name_tag:
            financial_data["company_name"] = name_tag.get_text(strip=True)

        # BSE / NSE codes
        company_info = soup.find("div", class_=re.compile("company-info|company-ratios"))
        if company_info:
            info_text = company_info.get_text()
            bse_match = re.search(r"BSE:\s*(\d+)", info_text)
            if bse_match:
                financial_data["bse_code"] = bse_match.group(1)
            nse_match = re.search(r"NSE:\s*(\w+)", info_text)
            if nse_match:
                financial_data["nse_code"] = nse_match.group(1)

        # Extract from ratio list items
        ratio_items = soup.find_all("li", class_=re.compile("ratio|metric|flex"))
        for item in ratio_items:
            text = item.get_text(strip=True)
            text_lower = text.lower()
            value = extract_number(text)
            if not value:
                continue
            for patterns, key in metrics_to_extract:
                if any(p in text_lower for p in patterns) and not financial_data.get(key):
                    add_if_exists(key, value)
                    break

        # Extract from tables (P&L / balance sheet latest row)
        table_metrics = [
            (["sales", "revenue"], "revenue"),
            (["operating profit", "ebit"], "operating_profit"),
            (["net profit", "pat"], "net_profit"),
            (["ebitda"], "ebitda"),
            (["total assets"], "total_assets"),
            (["total liabilities"], "total_liabilities"),
            (["net worth", "shareholder equity"], "net_worth"),
            (["reserves"], "reserves"),
            (["borrowings"], "borrowings"),
            (["operating cash flow", "cash from operations"], "operating_cash_flow"),
            (["free cash flow"], "free_cash_flow"),
        ]
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    num_value = extract_number(cells[-1].get_text(strip=True))
                    if num_value:
                        for patterns, key in table_metrics:
                            if any(p in label for p in patterns) and not financial_data.get(key):
                                add_if_exists(key, num_value)
                                break

        # Sector
        sector_tag = soup.find(string=re.compile(r"Sector|Industry"))
        if sector_tag:
            parent = sector_tag.find_parent()
            if parent:
                next_elem = parent.find_next_sibling()
                if next_elem:
                    financial_data["sector"] = next_elem.get_text(strip=True)

        return financial_data

    def extract_company_profile(self, soup: BeautifulSoup) -> Dict:
        """
        Extract company profile: key-value list items and descriptive paragraphs.

        Returns:
            Dict with profile fields; 'description' key holds combined paragraph text.
        """
        profile: Dict = {}
        company_profile = soup.find("div", class_="company-profile")
        if not company_profile:
            return profile

        for item in company_profile.find_all("li"):
            label_elem = item.find("span", class_="name") or item.find("b")
            if label_elem:
                label = label_elem.get_text(strip=True).rstrip(":")
                value_text = item.get_text(strip=True)
                value = value_text.replace(label, "", 1).strip().lstrip(":").strip()
                if label and value:
                    profile[label] = value

        paragraphs = [p.get_text(strip=True) for p in company_profile.find_all("p") if p.get_text(strip=True)]
        if paragraphs:
            profile["description"] = " ".join(paragraphs)

        return profile

    def extract_section_tables(self, soup: BeautifulSoup) -> Dict:
        """
        Extract structured tables from key financial sections:
        profit-loss, balance-sheet, cash-flow, ratios, shareholding.

        Returns:
            Dict keyed by section id; values are lists of {'headers': [...], 'rows': [[...], ...]}.
        """
        sections: Dict = {}
        target_ids = ["profit-loss", "balance-sheet", "cash-flow", "ratios", "shareholding"]

        for section_id in target_ids:
            section = soup.find("section", id=section_id)
            if not section:
                continue

            tables_data = []
            for table in section.find_all("table"):
                headers: List[str] = []
                thead = table.find("thead")
                if thead:
                    header_row = thead.find("tr")
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

                rows: List[List[str]] = []
                tbody = table.find("tbody") or table
                for tr in tbody.find_all("tr"):
                    row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if row:
                        rows.append(row)

                if headers or rows:
                    tables_data.append({"headers": headers, "rows": rows})

            if tables_data:
                sections[section_id] = tables_data

        return sections

    # ------------------------------------------------------------------
    # Document links extraction
    # ------------------------------------------------------------------

    def extract_file_links(self, company_url: str) -> Dict[str, List[Dict]]:
        """
        Extract document links from the Documents section and the /concalls/ page.

        Returns:
            Dict with keys: annual_reports, quarterly_results, concall_transcripts,
            investor_presentations, shareholding_patterns, corporate_announcements,
            credit_ratings, board_meetings, other_documents.
            Each value is a list of dicts with keys: title, url, doc_type, year, quarter, date.
        """
        result: Dict[str, List[Dict]] = {
            "annual_reports": [],
            "quarterly_results": [],
            "concall_transcripts": [],
            "investor_presentations": [],
            "shareholding_patterns": [],
            "corporate_announcements": [],
            "credit_ratings": [],
            "board_meetings": [],
            "other_documents": [],
        }

        soup = self.get_company_page(company_url)
        if not soup:
            return result

        def _meta(title: str) -> Dict:
            year_m = re.search(r"20\d{2}|FY\s*\d{2}", title)
            qtr_m = re.search(r"Q[1-4]|quarter\s*[1-4]", title, re.I)
            date_m = re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}", title)
            return {
                "year": year_m.group(0) if year_m else "Unknown",
                "quarter": qtr_m.group(0).upper() if qtr_m else "N/A",
                "date": date_m.group(0) if date_m else "N/A",
            }

        def _categorize(title: str, href: str):
            tl = title.lower()
            if any(kw in tl for kw in ["annual report", "annual result", "audited", "yearly"]):
                return "annual_reports", "Annual Report"
            if any(kw in tl for kw in ["quarterly result", "quarterly financial", "q1", "q2", "q3", "q4", "unaudited"]):
                return "quarterly_results", "Quarterly Result"
            if any(kw in tl for kw in ["concall", "transcript", "earnings call", "conference call"]):
                return "concall_transcripts", "Conference Call Transcript"
            if any(kw in tl for kw in ["investor presentation", "presentation", "investor deck", "earnings presentation"]):
                return "investor_presentations", "Investor Presentation"
            if any(kw in tl for kw in ["shareholding pattern", "share holding", "holding pattern"]):
                return "shareholding_patterns", "Shareholding Pattern"
            if any(kw in tl for kw in ["announcement", "notice", "disclosure", "intimation", "outcome"]):
                return "corporate_announcements", "Corporate Announcement"
            if any(kw in tl for kw in ["credit rating", "rating", "crisil", "icra", "care", "brickwork"]):
                return "credit_ratings", "Credit Rating"
            if any(kw in tl for kw in ["board meeting", "board outcome"]):
                return "board_meetings", "Board Meeting"
            return "other_documents", "Other"

        def _add(title: str, href: str):
            if not title or not href:
                return
            if href.startswith("/"):
                href = f"{self.BASE_URL}{href}"
            category, doc_type = _categorize(title, href)
            result[category].append({"title": title, "url": href, "doc_type": doc_type, **_meta(title)})

        # Locate Documents section
        documents_section = (
            soup.find(["section", "div"], id=re.compile(r"documents?", re.I))
            or soup.find(["section", "div"], class_=re.compile(r"documents?", re.I))
        )
        if not documents_section:
            doc_heading = soup.find(["h2", "h3", "h4"], string=re.compile(r"documents?", re.I))
            if doc_heading:
                documents_section = doc_heading.find_parent(["section", "div"])

        if documents_section:
            for link in documents_section.find_all("a", href=True):
                _add(link.get_text(strip=True) or link.get("title", ""), link["href"])
        else:
            # Fallback: grab all PDF links from the full page
            for link in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
                _add(link.get_text(strip=True) or link["href"], link["href"])

        # Dedicated /concalls/ page
        concall_soup = self.get_company_page(company_url.rstrip("/") + "/concalls/")
        if concall_soup:
            for link in concall_soup.find_all("a", href=True):
                href = link["href"]
                title = link.get_text(strip=True) or href
                is_doc = any(ext in href.lower() for ext in [".pdf", ".xls", ".xlsx"])
                is_concall = any(kw in title.lower() for kw in ["transcript", "concall", "conference"])
                if is_doc or is_concall:
                    if href.startswith("/"):
                        href = f"{self.BASE_URL}{href}"
                    result["concall_transcripts"].append(
                        {"title": title, "url": href, "doc_type": "Conference Call Transcript", **_meta(title)}
                    )

        # Deduplicate within each category
        for category in result:
            seen: set = set()
            unique = []
            for doc in result[category]:
                if doc["url"] not in seen:
                    seen.add(doc["url"])
                    unique.append(doc)
            result[category] = unique

        return result

    # ------------------------------------------------------------------
    # File download (optional helper)
    # ------------------------------------------------------------------

    # def download_file(self, url: str, filename: str, subfolder: str = "reports") -> Optional[str]:
    #     """
    #     Download a file from URL to the local data directory.
    #
    #     Returns:
    #         Local file path string or None if download failed.
    #     """
    #     save_dir = self.data_dir / subfolder
    #     filepath = save_dir / filename
    #
    #     if filepath.exists():
    #         return str(filepath)
    #
    #     try:
    #         response = self.session.get(url, timeout=30, stream=True)
    #         response.raise_for_status()
    #         save_dir.mkdir(parents=True, exist_ok=True)
    #         with open(filepath, "wb") as f:
    #             for chunk in response.iter_content(chunk_size=8192):
    #                 f.write(chunk)
    #         return str(filepath)
    #     except Exception:
    #         return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_fetcher_instance: Optional[ScreenerFetcher] = None


def get_fetcher() -> ScreenerFetcher:
    """Return the module-level singleton ScreenerFetcher instance."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = ScreenerFetcher()
    return _fetcher_instance
