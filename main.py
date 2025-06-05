import pandas as pd
import whois
import tldextract
import requests
import time
import re
import urllib.parse

df = pd.read_csv('/content/websites.csv')


def get_company_name_from_whois(domain):
    try:
        w = whois.whois(domain + ".com")
        name = w.org or w.name
        if not name or "not disclosed" in name.lower():
            return domain.capitalize()
        return name
    except:
        return domain.capitalize()

# for ticker search
def clean_company_name(name):
    return (
        name.replace("Inc.", "")
            .replace("Corporation", "")
            .replace("Ltd.", "")
            .replace("LLC", "")
            .replace(",", "")
            .strip()
    )

# guessing for fallback name searches 
def generate_guess_names(domain):
    base = domain.capitalize()
    return [
        base,
        base + " Inc.",
        base + " Corporation",
        base + " Technologies",
        base + " Ltd",
        base + " Systems",
    ]



"""try to find the data from yfinance api from yahoo search, if that fails then
  trying to attempt to guess the company name for advance searching """


headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_ticker(company_name, domain=None):
    try:
        search_terms = [clean_company_name(company_name)]

        # If WHOIS fails then we guess the names from domain
        if domain:
            search_terms += generate_guess_names(domain)

        for term in search_terms:
            if not term:
                continue
            encoded = urllib.parse.quote(term)
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={encoded}"
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()

            for item in data.get("quotes", []):
                if item.get("quoteType") == "EQUITY":
                    full = (item.get("shortname", "") + item.get("longname", "")).lower()
                    if term.lower() in full:
                        return item.get("symbol")

            # Fallback: return first EQUITY result
            for item in data.get("quotes", []):
                if item.get("quoteType") == "EQUITY":
                    return item.get("symbol")

        return ""
    except Exception as e:
        print(f"Error getting ticker for {company_name}: {e}")
        return "")

#caching for duplications


whois_cache = {}

def safe_whois_lookup(domain):
    if domain in whois_cache:
        return whois_cache[domain]
    name = get_company_name_from_whois(domain)
    whois_cache[domain] = name
    time.sleep(1)
    return name


df["DOMAIN"] = df["URL"].apply(lambda url: tldextract.extract(url).domain)
df["NAME"] = df["DOMAIN"].apply(safe_whois_lookup)

df["CLEANED_NAME"] = df["NAME"].apply(clean_company_name)

#ticker caching 

ticker_cache = {}

def safe_ticker_lookup(row):
    name = row["CLEANED_NAME"]
    domain = row["DOMAIN"]
    if name in ticker_cache:
        return ticker_cache[name]
    ticker = get_ticker(name, domain=domain)
    ticker_cache[name] = ticker
    time.sleep(1)
    return ticker

df["TICKER"] = df.apply(safe_ticker_lookup, axis=1)


df.to_csv("extraction.csv", index=False)
print("an Extraction file is saved!!")