from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import Stock, OHLCData, LiveQuote, Index, IndexOHLCData, IndexQuote
from .services import get_flattrade_service

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

    # Get interval from request, default to 5 minutes
    interval = request.GET.get('interval', 5)
    
    # Validate interval - must be one of the supported values
    valid_intervals = [1, 3, 5, 15, 30, 60]
    try:
        interval = int(interval)
        if interval not in valid_intervals:
            interval = 5  # fallback to default
    except (ValueError, TypeError):
        interval = 5  # fallback to default

    # Check if we have recent data (within last 5 minutes) to avoid API calls
    from django.utils import timezone
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    
    recent_ohlc = OHLCData.objects.filter(
        stock=stock,
        interval=interval,
        timestamp__gte=five_minutes_ago
    ).exists()
    
    recent_quote = LiveQuote.objects.filter(
        stock=stock,
        timestamp__gte=five_minutes_ago
    ).exists()
    
    # Only refresh if we don't have recent data
    if not recent_ohlc or not recent_quote:
        flattrade_service = get_flattrade_service()
        if not recent_ohlc:
            flattrade_service.get_ohlc_data(stock.symbol, interval)
        if not recent_quote:
            flattrade_service.get_live_quote(stock.symbol)

    # Get OHLC data for the stock with selected interval
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
        'interval': interval,
        'valid_intervals': valid_intervals
    }

    return render(request, 'stock_data/stock_detail.html', context)

def index_detail(request, index_id):
    """Index detail view showing OHLC data"""
    index = get_object_or_404(Index, id=index_id)

    # Get interval from request, default to 5 minutes
    interval = request.GET.get('interval', 5)
    
    # Validate interval - must be one of the supported values
    valid_intervals = [1, 3, 5, 15, 30, 60]
    try:
        interval = int(interval)
        if interval not in valid_intervals:
            interval = 5  # fallback to default
    except (ValueError, TypeError):
        interval = 5  # fallback to default

    # Check if we have recent data (within last 5 minutes) to avoid API calls
    from django.utils import timezone
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    
    recent_ohlc = IndexOHLCData.objects.filter(
        index=index,
        interval=interval,
        timestamp__gte=five_minutes_ago
    ).exists()
    
    recent_quote = IndexQuote.objects.filter(
        index=index,
        timestamp__gte=five_minutes_ago
    ).exists()
    
    # Only refresh if we don't have recent data
    if not recent_ohlc or not recent_quote:
        flattrade_service = get_flattrade_service()
        if not recent_ohlc:
            flattrade_service.get_index_ohlc_data(index.symbol, interval)
        if not recent_quote:
            flattrade_service.get_index_quote(index.symbol)

    # Get OHLC data for the index with selected interval
    ohlc_data = IndexOHLCData.objects.filter(
        index=index,
        interval=interval
    ).order_by('-timestamp')

    # Pagination
    paginator = Paginator(ohlc_data, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get latest live quote
    latest_quote = IndexQuote.objects.filter(index=index).order_by('-timestamp').first()

    context = {
        'index': index,
        'stock': index,  # For template compatibility
        'ohlc_data': page_obj,
        'latest_quote': latest_quote,
        'interval': interval,
        'valid_intervals': valid_intervals,
        'is_index': True
    }

    return render(request, 'stock_data/index_detail.html', context)

def search_stocks(request):
    """Search stocks view"""
    query = request.GET.get('q', '')
    stocks = []
    
    if query:
        # Search in database first
        db_stocks = Stock.objects.filter(
            Q(symbol__icontains=query) | Q(company_name__icontains=query)
        )
        
        # Check cache first to avoid repeated API calls
        from django.core.cache import cache
        cache_key = f'search_{query.lower().replace(" ", "_")}'
        cached_results = cache.get(cache_key)
        
        if cached_results:
            stocks = cached_results
        elif 'nifty' in query.lower() or not db_stocks:
            flattrade_service = get_flattrade_service()
            api_stocks = flattrade_service.search_stocks(query)
            
            # Combine database and API results, removing duplicates
            all_stocks = list(db_stocks) + [s for s in api_stocks if s not in db_stocks]
            stocks = all_stocks
            
            # Cache results for 10 minutes
            cache.set(cache_key, stocks, 600)
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
    
    flattrade_service = get_flattrade_service()
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
    
    # Get interval from request, default to 5 minutes
    interval = request.GET.get('interval', 5)
    
    # Validate interval
    valid_intervals = [1, 3, 5, 15, 30, 60]
    try:
        interval = int(interval)
        if interval not in valid_intervals:
            interval = 5  # fallback to default
    except (ValueError, TypeError):
        interval = 5  # fallback to default
    
    flattrade_service = get_flattrade_service()
    ohlc_records = flattrade_service.get_ohlc_data(stock.symbol, interval)
    
    if ohlc_records:
        data = {
            'success': True,
            'interval': interval,
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
    
    # Get interval from request, default to 5 minutes
    interval = request.GET.get('interval', 5)
    
    # Validate interval
    valid_intervals = [1, 3, 5, 15, 30, 60]
    try:
        interval = int(interval)
        if interval not in valid_intervals:
            interval = 5  # fallback to default
    except (ValueError, TypeError):
        interval = 5  # fallback to default
    
    flattrade_service = get_flattrade_service()
    
    # Refresh OHLC data with selected interval
    ohlc_records = flattrade_service.get_ohlc_data(stock.symbol, interval)
    
    # Refresh live quote
    live_quote = flattrade_service.get_live_quote(stock.symbol)
    
    if ohlc_records or live_quote:
        messages.success(request, f'Data refreshed for {stock.symbol} ({interval} min intervals)')
    else:
        messages.error(request, f'Failed to refresh data for {stock.symbol}')
    
    # Redirect back with interval parameter preserved
    redirect_url = f'/stock/{stock_id}/'
    if interval != 5:  # Only add parameter if not default
        redirect_url += f'?interval={interval}'
    
    return redirect(redirect_url)

@require_http_methods(["POST"])
@csrf_exempt
def refresh_data_async(request, stock_id):
    """Asynchronously refresh stock data without blocking UI"""
    try:
        stock = get_object_or_404(Stock, id=stock_id)
        interval = request.POST.get('interval', 5)
        
        # Validate interval
        valid_intervals = [1, 3, 5, 15, 30, 60]
        try:
            interval = int(interval)
            if interval not in valid_intervals:
                interval = 5
        except (ValueError, TypeError):
            interval = 5
        
        # Refresh data in background
        flattrade_service = get_flattrade_service()
        ohlc_records = flattrade_service.get_ohlc_data(stock.symbol, interval)
        live_quote = flattrade_service.get_live_quote(stock.symbol)
        
        return JsonResponse({
            'success': True,
            'message': f'Data refreshed for {stock.symbol}',
            'ohlc_count': len(ohlc_records) if ohlc_records else 0,
            'has_quote': live_quote is not None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["POST"])
@csrf_exempt
def refresh_index_data_async(request, index_id):
    """Asynchronously refresh index data without blocking UI"""
    try:
        index = get_object_or_404(Index, id=index_id)
        interval = request.POST.get('interval', 5)
        
        # Validate interval
        valid_intervals = [1, 3, 5, 15, 30, 60]
        try:
            interval = int(interval)
            if interval not in valid_intervals:
                interval = 5
        except (ValueError, TypeError):
            interval = 5
        
        # Refresh data in background
        flattrade_service = get_flattrade_service()
        ohlc_records = flattrade_service.get_index_ohlc_data(index.symbol, interval)
        index_quote = flattrade_service.get_index_quote(index.symbol)
        
        return JsonResponse({
            'success': True,
            'message': f'Data refreshed for {index.symbol}',
            'ohlc_count': len(ohlc_records) if ohlc_records else 0,
            'has_quote': index_quote is not None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
