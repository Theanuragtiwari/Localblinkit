from fastapi.responses import JSONResponse


def success(data=None, message='OK', status_code=200):
    return JSONResponse(status_code=status_code, content={
        'success': True,
        'message': message,
        'error_code': None,
        'data': data,
    })


def error(message='Error', error_code='ERROR', status_code=400, data=None):
    return JSONResponse(status_code=status_code, content={
        'success': False,
        'message': message,
        'error_code': error_code,
        'data': data,
    })
