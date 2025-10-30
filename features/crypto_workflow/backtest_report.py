import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_html_report(result: dict, outdir: Path) -> None:
    """Generate HTML report with interactive plots"""
    eq_curve = result.get('equity_curve')
    if eq_curve is None or eq_curve.empty:
        return
    
    # Create figure with secondary y-axis
    fig = make_subplots(rows=2, cols=1, 
                       subplot_titles=('Equity Curve', 'Trade Signals'),
                       vertical_spacing=0.12,
                       row_heights=[0.7, 0.3])
    
    # Add equity curve
    fig.add_trace(
        go.Scatter(x=eq_curve['ts'], y=eq_curve['equity'],
                  name='Portfolio Value',
                  line=dict(color='blue')),
        row=1, col=1
    )
    
    # Add trades if available
    trades = result.get('trades')
    if trades is not None and not trades.empty:
        # Buy signals
        buys = trades[trades['trade'] > 0]
        fig.add_trace(
            go.Scatter(x=buys['ts'], y=buys['equity'],
                      mode='markers',
                      name='Buy',
                      marker=dict(color='green', symbol='triangle-up', size=10)),
            row=1, col=1
        )
        
        # Sell signals  
        sells = trades[trades['trade'] < 0]
        fig.add_trace(
            go.Scatter(x=sells['ts'], y=sells['equity'],
                      mode='markers', 
                      name='Sell',
                      marker=dict(color='red', symbol='triangle-down', size=10)),
            row=1, col=1
        )
        
        # Position size
        fig.add_trace(
            go.Scatter(x=trades['ts'], y=trades['position'],
                      name='Position Size',
                      line=dict(color='purple')),
            row=2, col=1
        )
    
    # Update layout
    fig.update_layout(
        title='Backtest Results',
        xaxis_title='Time',
        yaxis_title='Portfolio Value',
        yaxis2_title='Position Size',
        showlegend=True,
        height=800
    )
    
    # Save HTML
    fig.write_html(outdir / 'report.html')

def write_backtest_report(backtest_result: dict, outdir: Path) -> None:
    """Write backtest results to files"""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Write metrics JSON
    metrics = backtest_result.get('metrics', {})
    metrics['generated_at'] = datetime.now().isoformat()
    with open(outdir / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # Write trades
    trades = backtest_result.get('trades')
    if trades is not None and not trades.empty:
        trades.to_csv(outdir / 'trades.csv', index=False)
        trades.to_parquet(outdir / 'trades.parquet', index=False)
    
    # Write equity curve
    eq = backtest_result.get('equity_curve')
    if eq is not None and not eq.empty:
        eq.to_parquet(outdir / 'equity_curve.parquet', index=False)
        eq.to_csv(outdir / 'equity_curve.csv', index=False)
    
    # Generate HTML report
    try:
        create_html_report(backtest_result, outdir)
    except Exception as e:
        logger.warning(f"Failed to generate HTML report: {str(e)}")
