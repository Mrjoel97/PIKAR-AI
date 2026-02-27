
try:
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from fastapi import FastAPI
    import sys
    
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    
    print("Attempting to add middleware with kwargs...")
    try:
        app.add_middleware(SlowAPIMiddleware, limiter=limiter)
        print("Success with kwargs!")
    except Exception as e:
        print(f"Failed with kwargs: {e}")
        
    app = FastAPI()
    print("Attempting to add middleware without kwargs...")
    try:
        app.add_middleware(SlowAPIMiddleware)
        print("Success without kwargs!")
    except Exception as e:
        print(f"Failed without kwargs: {e}")

except ImportError as e:
    print(f"Import failed: {e}")
