
import inspect
from slowapi.middleware import SlowAPIMiddleware

print(f"Signature: {inspect.signature(SlowAPIMiddleware.__init__)}")
