# Rate limiting — Redis disabled for local development
# In production, enable Redis and uncomment the full implementation

async def check_verify_rate_limit(key: str):
    return True, None

async def close_redis():
    pass