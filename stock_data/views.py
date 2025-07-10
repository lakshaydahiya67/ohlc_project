from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, timedelta

from .models import Stock, OHLCData, LiveQuote
from .services import FlattradeService

def dashboard(request):
    """Main dashboard view"""
    # Get stocks from database (instead of calling API every time)
    popular_stocks = Stock.objects.all()[:10]
    
    # Get recent OHLC data
    recent_ohlc = OHLCData.objects.select_related('stock').order_by('-timestamp')[:10]
    
    # Get recent live quotes
    recent_quotes = LiveQuote.objects.select_related('stock').order_by('-timestamp')[:10]
    
    # Get some stats for the dashboard
    total_stocks = Stock.objects.count()
    total_ohlc_records = OHLCData.objects.count()
    total_quotes = LiveQuote.objects.count()
    
    context = {
        'popular_stocks': popular_stocks,
        'recent_ohlc': recent_ohlc,
        'recent_quotes': recent_quotes,
        'total_stocks': total_stocks,
        'total_ohlc_records': total_ohlc_records,
        'total_quotes': total_quotes,
    }
    
    return render(request, 'stock_data/dashboard.html', context)

def stock_detail(request, stock_id):
    """Stock detail view showing OHLC data"""
    stock = get_object_or_404(Stock, id=stock_id)

    # Always refresh data before showing the page
    flattrade_service = FlattradeService()
    flattrade_service.get_ohlc_data(stock.symbol, 5)
    flattrade_service.get_live_quote(stock.symbol)

    # Fixed to 5-minute intervals only
    interval = 5

    # Get OHLC data for the stock
    ohlc_data = OHLCData.objects.filter(
        stock=stock,
        interval=interval
    ).order_by('-timestamp')

    # Pagination
    paginator = Paginator(ohlc_data, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get latest live quote
    latest_quote = LiveQuote.objects.filter(stock=stock).order_by('-timestamp').first()

    context = {
        'stock': stock,
        'ohlc_data': page_obj,
        'latest_quote': latest_quote,
        'interval': interval
    }

    return render(request, 'stock_data/stock_detail.html', context)

def search_stocks(request):
    """Search stocks view"""
    query = request.GET.get('q', '')
    stocks = []
    
    if query:
        # Search in database first
        db_stocks = Stock.objects.filter(
            Q(symbol__icontains=query) | Q(company_name__icontains=query)
        )
        
        # For 'nifty' searches, always search API to include discovery
        # For other searches, only search API if no database results
        if 'nifty' in query.lower() or not db_stocks:
            flattrade_service = FlattradeService()
            api_stocks = flattrade_service.search_stocks(query)
            
            # Combine database and API results, removing duplicates
            all_stocks = list(db_stocks) + [s for s in api_stocks if s not in db_stocks]
            stocks = all_stocks
        else:
            stocks = db_stocks
    
    context = {
        'query': query,
        'stocks': stocks,
    }
    
    return render(request, 'stock_data/search.html', context)

def get_live_quote(request, stock_id):
    """AJAX endpoint to get live quote"""
    stock = get_object_or_404(Stock, id=stock_id)
    
    flattrade_service = FlattradeService()
    live_quote = flattrade_service.get_live_quote(stock.symbol)
    
    if live_quote:
        data = {
            'success': True,
            'ltp': float(live_quote.ltp),
            'open': float(live_quote.open_price),
            'high': float(live_quote.high_price),
            'low': float(live_quote.low_price),
            'change': float(live_quote.change),
            'change_percent': float(live_quote.change_percent),
            'volume': live_quote.volume,
            'timestamp': live_quote.timestamp.isoformat()
        }
    else:
        data = {
            'success': False,
            'error': 'Failed to fetch live quote'
        }
    
    return JsonResponse(data)

def get_ohlc_data(request, stock_id):
    """AJAX endpoint to get OHLC data"""
    stock = get_object_or_404(Stock, id=stock_id)
    
    # Fixed to 5-minute intervals only
    interval = 5
    
    flattrade_service = FlattradeService()
    ohlc_records = flattrade_service.get_ohlc_data(stock.symbol, interval)
    
    if ohlc_records:
        data = {
            'success': True,
            'data': [
                {
                    'timestamp': record.timestamp.isoformat(),
                    'open': float(record.open_price),
                    'high': float(record.high_price),
                    'low': float(record.low_price),
                    'close': float(record.close_price),
                    'volume': record.volume
                }
                for record in ohlc_records
            ]
        }
    else:
        data = {
            'success': False,
            'error': 'Failed to fetch OHLC data'
        }
    
    return JsonResponse(data)


def refresh_stock_data(request, stock_id):
    """Refresh stock data (OHLC and live quote)"""
    stock = get_object_or_404(Stock, id=stock_id)
    
    flattrade_service = FlattradeService()
    
    # Refresh OHLC data with 5-minute intervals
    ohlc_records = flattrade_service.get_ohlc_data(stock.symbol, 5)
    
    # Refresh live quote
    live_quote = flattrade_service.get_live_quote(stock.symbol)
    
    if ohlc_records or live_quote:
        messages.success(request, f'Data refreshed for {stock.symbol}')
    else:
        messages.error(request, f'Failed to refresh data for {stock.symbol}')
    
    return redirect('stock_detail', stock_id=stock_id)
