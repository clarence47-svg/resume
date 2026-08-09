async def acquire_page(context):
    if context.pages:
        return context.pages[-1]
    return await context.new_page()
