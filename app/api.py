import httpx

from .cache import Cache
from datetime import datetime
from flask import (
    Blueprint,
    Response,
    make_response,
    current_app)

bp = Blueprint('api', __name__, url_prefix='/')
cache = Cache(max_size=1024)

@bp.route('/<image_id>', methods=['GET'])
def pixiv_image_proxy(image_id: str):
    current_app.logger.info(f'[Image_Get] {image_id}')
    return get_image(image_id)
    # return make_response('Not Implemented', 404)

def get_image(image_id: str) -> Response:
    """get pixiv image (preferred cache use)

    Args:
        image_id (str): image id

    Returns:
        bytes: image data
    """

    # check cache
    img = cache.get(image_id)
    if not img:
        
        # parser pid and image index
        pid, img_idx = get_pid(image_id)

        # get access token
        access_token = get_pixiv_token()
        if not access_token:
            current_app.logger.warning(
                f'[Token_Get] can\'t get access_token, try again later')
            return make_response('Token Error', 401)
        # get image url
        img_url_list = get_img_url(pid, access_token)
        if img_url_list[0] == 'error':
            current_app.logger.warning(
                f'[Illust_Get] can\'t get image url, try again later')
            return make_response(img_url_list[2], img_url_list[1])
        # get image data
        img_data = download_image(img_url_list, img_idx)
        if type(img_data) == list:
            current_app.logger.warning(
                f'[Image_Get] can\'t get image data, try again later')
            return make_response(img_data[1], img_data[0])
        # update cache
        try:
            timeout = current_app.config['CACHE_EXPIRA_TIME']
        except KeyError:
            timeout = 259200
        cache.update(image_id, img_data, timeout)
        
    else:
        img_data = img
    
    # return image data
    headers = {
        'Content-Type': 'image/jpeg',
        # 'location': img_url_list[img_idx],
    }
    return make_response(img_data, 200, headers)
        
def download_image(imgs_url: list[str], img_idx: int) -> bytes | list:
    """download image data from url

    Args:
        img_url (str): image url
        img_idx (int): image index in multi-image illust

    Returns:
        bytes: image data successfully downloaded\n
        **list**\n
            if failed, return `[error_code, error_message]`
    """
    if len(imgs_url) >= img_idx + 1:
        img_url = imgs_url[img_idx]
    else:
        current_app.logger.warning(
            f'[Image_Get] image index out of range, try again later')
        return [404, 'Image index out of range']
    try:
        current_app.logger.info(f'[Image_Get] {img_url}')
        res = httpx.get(
            url = img_url,
            headers = {
                # 'host': 'i.pximg.net',
                # 'app-os': 'ios',
                # 'app-os-version': '14.6',
                'user-agent': 'Fuck UA Header',
                # 'Authorization': f"Bearer {access_token}",
                # 'accept-language': 'zh-cn',
                'Referer': 'https://www.pixiv.net/'
            },
            proxy=current_app.config.get('PROXY')
        )
        if res.status_code == 200:
            return res.content
        else:
            current_app.logger.warning(
                f'[Image_Get] can\'t get image data, HTTP Code: {res.status_code}')
            return [res.status_code, 'Can\'t get image data']
    except httpx.ConnectError as e:
        current_app.logger.warning(
            f'[Image_Get] can\'t connect to server, {e}')
        return [402, 'Can\'t connect to server']
        

def get_pid(image_id: str) -> tuple[int,int]:
    """get pixiv illust id and page index from image_id

    Args:
        image_id (str): image id

    Returns:
        tuple[int,int]:
            first element is `pid`, second element is `img_idx`\n
            if failed, return `(-1,error_code)`
    """
    try:
        p_split = image_id.split('-')
        pid = int(p_split[0])
        if len(p_split) != 1:
            image_id = int(p_split[1])
        else:
            image_id = 0
    except ValueError:
        return (-1,404)  # 输入参数错误
    return (pid,image_id)

def get_img_url(pid: int, access_token: str) -> list:
    """get image url from pixiv api

    Args:
        pid (int): pixiv illust id
        access_token (str): access token

    Returns:
        list[str]: image url list, if failed first element is `'error'`\n
        and second element is error code, is `int`, thirds element is\n
        error message
    """
    
    pixiv_api = 'https://app-api.pixiv.net/v1/illust/detail'
    headers = {
        # 'host': 'app-api.pixiv.net',
        # 'app-os': 'ios',
        # 'app-os-version': '14.6',
        # 'user-agent': 'PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)',
        'Authorization': 'Bearer %s' % access_token,
        # 'accept-language': 'zh-cn'
    }
    params = {'illust_id': pid}
    res = httpx.get(
        url=pixiv_api,
        headers=headers,
        params=params,
        proxy=current_app.config.get('PROXY')
    )

    match res.status_code:
        case 200:
            pass
        case 404:
            current_app.logger.warning(
                f'[Illust_Get] can\'t find image, HTTP Code: {res.status_code}')
            return ['error', res.status_code,
                    res.content.decode('unicode-escape')]
        case 500:
            current_app.logger.warning(
                f'[Illust_Get] too many requests, HTTP Code: {res.status_code}')
            return ['error', res.status_code,
                    res.content.decode('unicode-escape')]
        case _:
            current_app.logger.warning(
                f'[Illust_Get] unknown error, HTTP Code: {res.status_code}')
            return ['error', res.status_code,
                    res.content.decode('unicode-escape')]
    
    data = res.json()
    current_app.logger.info(f'[Illust_Get] {data}')
    try:
        # get the number of pages
        page_count = data['illust']['page_count']
        images_url = []
        
        # single image
        if page_count == 1:
            images_url.append(
                data['illust']['meta_single_page']['original_image_url']
            )
        # multi images
        else:
            pages = data['illust']['meta_pages']
            for page in pages:
                images_url.append(page['image_urls']['original'])
        return images_url
    except KeyError as e:
        current_app.logger.error(
            f'[Illust_Get] get image failed, KeyError: {e}')
        return

def get_pixiv_token(count: int = 0) -> str | None:
    """get pixiv access_token

    Returns:
        **str**:
            if success, return `access_token`\n
        **None**\n
            if failed, return `None`
    """    
    if count > 3:
        current_app.logger.error(
            f'[Token_Refresh] get token failed, try again later')
        return
    
    # get refresh_token and access_token from config
    refresh_token = current_app.config['PIXIV_REFRESH_TOKEN']
    access_token: dict = current_app.config['PIXIV_ACCESS_TOKEN']
    current_app.logger.info(f'[Token_Cache] {access_token}')
    
    # check token expire time
    if access_token['expireAt'] - 500 < datetime.now().timestamp():
        
        # refresh token
        res: httpx.Response = httpx.post(
            url="https://oauth.secure.pixiv.net/auth/token",
            data={
                "client_id": "MOBrBDS8blbauoSck0ZfDbtuzpyT",
                "client_secret": "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj",
                "grant_type": "refresh_token",
                "include_policy": "true",
                "refresh_token": refresh_token,
            },
            headers={"User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"}, 
            proxy=current_app.config.get('PROXY')
        )
        
        # check refresh result faile
        if res.status_code != 200:
            current_app.logger.warning(
                f'[Token_Refresh] get token failed')
            current_app.logger.warning(
                f'[Token_Refresh] HTTP Code: {res.status_code}, Try again...')
            return get_pixiv_token(count+1)
        
        data = res.json()
        current_app.logger.info(f'[Token_Refresh] {data}')
        
        # update access_token to config
        access_token.update({
            'value': data['access_token'],
            'expireAt': round(datetime.now().timestamp()) + 3600,
        })
        current_app.config['PIXIV_ACCESS_TOKEN'] = access_token
    return access_token['value']