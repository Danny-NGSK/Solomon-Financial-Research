from src.data_loader.market_loader import load_market_data
from src.data_loader.industry_loader import load_industry_data
from src.data_loader.company_loader import load_company_data

from src.analysis.market_analysis import analyze_market
from src.analysis.industry_analysis import analyze_industry
from src.analysis.company_analysis import analyze_company
from src.analysis.signal_extractor import extract_signals

from src.llm.report_generator import generate_report

def main():
    print("🚀 Financial AI Agent MVP (Alpha Vantage Version) Starting...\n")
    
    print("[1/3] Loading Market, Industry, and Company data...")
    market_data = load_market_data()
    industry_data = load_industry_data()
    company_data = load_company_data()

    print("[2/3] Analyzing relative strength and trends...")
    market_result = analyze_market(market_data)
    industry_result = analyze_industry(industry_data)
    
    # ❌ 기존에 여기서 인자가 2개 들어갔을 확률이 높습니다. 1개로 맞춥니다.
    company_result = analyze_company(company_data)

    print("[3/3] Extracting signals and generating report...")
    signals = extract_signals(market_result, industry_result, company_result)
    report = generate_report(signals)

    print("\n=== SIGNALS ===")
    for key, value in signals.items():
        print(f"{key}: {value}")

    print("\n=== REPORT ===")
    print(report)

if __name__ == "__main__":
    main()