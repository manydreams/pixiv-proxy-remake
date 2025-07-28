from flask import Flask

def config(app: Flask):
    app.config.update(
        # application configuration
        PIXIV_REFRESH_TOKEN = '',
        CACHE_EXPIRA_TIME = 259200,     # 3 days
        
        # proxy, when get pixiv image and pixiv access token used
        # PROXY = 'http://127.0.0.1:20171',     
        
        
        # applocation constants 
        # (don't change unless you know what you're doing)
        PIXIV_ACCESS_TOKEN = {
            'value':    '',
            'expireAt':  0,    
        },
    )