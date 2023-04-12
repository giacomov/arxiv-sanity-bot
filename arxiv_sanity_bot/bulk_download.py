from requests_html import AsyncHTMLSession


async def get_link(async_session: AsyncHTMLSession, url):
    r = await async_session.get(url)
    return r


def bulk_download(urls):

    asession = AsyncHTMLSession()

    list_of_lambdas = [lambda url=url: get_link(asession, url) for url in urls]

    return asession.run(*list_of_lambdas)
