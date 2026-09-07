"""Playback is local; the Studio link is intentional external navigation."""
from playwright.sync_api import expect


def test_recording_playback_pause_scrub_and_reset(page, server, problems):
    requests = []
    page.on('request', lambda request: requests.append(request.url))
    page.goto(server + '/lab')
    expect(page.locator('#caseDetail')).to_be_visible()
    assert page.locator('#riskChart circle').count() > 0
    page.locator('#playSpeed').select_option('250')
    page.locator('#playBtn').click()
    page.wait_for_function("() => Number(document.getElementById('scrub').value) > 0")
    page.locator('#playBtn').click()
    expect(page.locator('#playBtn')).to_have_attribute('aria-pressed', 'false')
    shown = page.locator('#scrub').input_value()
    page.wait_for_timeout(400)
    assert page.locator('#scrub').input_value() == shown
    page.locator('#allBtn').click()
    expect(page.locator('#stepFwdBtn')).to_be_disabled()
    page.locator('#stepBackBtn').click()
    expect(page.locator('#stepFwdBtn')).to_be_enabled()
    page.locator('#playBtn').click()
    page.locator('#resetBtn').click()
    expect(page.locator('#caseDetail')).to_be_hidden()
    page.locator('.case-btn').last.click()
    expect(page.locator('#caseTitle')).to_have_text('When the network goes quiet')
    expect(page.locator('#outGrade')).to_have_text('UNRESOLVED')
    assert not any('/v1/console/run/' in url or '/v1/verify' in url for url in requests)
    assert problems == []


def test_google_studio_link_opens_correct_destination_without_key(page, server):
    observed = []

    def destination(route):
        observed.append(route.request.headers)
        route.fulfill(body='<title>Studio destination</title>')

    page.context.route('https://aistudio.google.com/**', destination)
    page.goto(server + '/lab')
    page.locator('#byok summary').click()
    link = page.locator('#googleStudioLink')
    expect(link).to_have_attribute('href', 'https://aistudio.google.com/apikey')
    expect(link).to_have_attribute('rel', 'noopener noreferrer')
    with page.expect_popup() as popup:
        link.click()
    popup.value.wait_for_url('https://aistudio.google.com/apikey')
    assert observed and 'x-isnad-gemini-key' not in observed[0]
    assert 'referer' not in observed[0]
    popup.value.close()
