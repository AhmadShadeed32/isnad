"""A personal model key follows page navigation, never unrelated requests."""
from playwright.sync_api import expect

KEY = "AIza-test-shared-key-000001"


def open_settings(page) -> None:
    """`/judge` keeps the planner and the key behind a *Demo settings*
    disclosure so the scenario is on the first screen; the other pages mount
    the same controls directly. Opening it here is what a reader does, and it
    is a no-op everywhere else."""
    settings = page.locator("#demoSettings")
    if settings.count() and not page.evaluate(
        "() => document.getElementById('demoSettings').open"
    ):
        settings.locator("> summary").click()


def test_key_follows_navigation_and_only_model_requests_receive_it(page, server):
    calls = []

    def model_request(route):
        calls.append(route.request.headers.get("x-isnad-gemini-key"))
        route.fulfill(status=503, json={"detail": {"message": "Offline test response"}})

    page.route("**/v1/console/run/**", model_request)
    page.goto(server + "/judge")
    page.evaluate("() => window.IsnadKey.ready")
    open_settings(page)
    page.locator('#byok summary').click()
    page.locator('#byokKey').fill(KEY)
    page.locator('#byokUse').click()
    expect(page.locator('#byokState')).to_contain_text('Saved')
    expect(page.locator('#byokKey')).to_have_value('')
    expect(page.locator('#checkout')).to_be_enabled()
    page.locator('#checkout').click()
    expect(page.locator('#fallback')).to_be_visible()
    assert calls == [KEY]

    for name in ('console', 'lab', 'privacy', 'judge'):
        page.locator(f'.site-nav a[href="/{name}"]').click()
        page.wait_for_url('**/' + name)
        page.evaluate("() => window.IsnadKey.ready")
        open_settings(page)
        expect(page.locator('#byokState')).to_contain_text('Saved')
        assert page.evaluate("IsnadKey.headers('/v1/privacy/posture')") == {}
        assert page.evaluate("IsnadKey.headers('https://example.com/v1/verify')") == {}
        assert page.evaluate("IsnadKey.headers('/v1/chains/test/explain')")["X-Isnad-Gemini-Key"] == KEY
        if name == 'console':
            page.locator('.btn[data-act="act6"]').click()
            expect(page.locator('.btn[data-act="act6"]')).to_be_enabled()
            assert calls == [KEY, KEY]

    page.locator('.site-nav a[href="/privacy"]').click()
    page.wait_for_url('**/privacy')
    page.locator('#byok summary').click()
    page.locator('#byokForget').click()
    page.locator('.site-nav a[href="/console"]').click()
    page.wait_for_url('**/console')
    page.evaluate("() => window.IsnadKey.ready")
    expect(page.locator('#byokState')).to_have_text('No key saved')
    assert page.evaluate("IsnadKey.headers('/v1/verify')") == {"X-Isnad-Planner": "greedy"}


def test_a_deployment_that_disables_keys_does_not_forward_a_saved_key(page, server):
    page.add_init_script(f"sessionStorage.setItem('isnad.byok.gemini', '{KEY}')")
    page.route('**/ui/settings.json', lambda route: route.fulfill(json={'accepts_request_key': False}))
    page.goto(server + '/lab')
    page.evaluate("() => window.IsnadKey.ready")
    page.locator('#byok summary').click()
    expect(page.locator('#byokUse')).to_be_disabled()
    assert page.evaluate("IsnadKey.headers('/v1/verify')") == {}
    page.locator('#byokForget').click()
    expect(page.locator('#byokState')).to_have_text('No key saved')


def test_switching_planners_keeps_the_key_but_only_sends_it_for_llm(page, server):
    page.goto(server + '/judge')
    page.evaluate('() => IsnadKey.ready')
    open_settings(page)
    page.locator('#plannerChoice').select_option('llm')
    expect(page.locator('#byokKey')).to_be_visible()
    expect(page.locator('#plannerChoice')).to_have_value('greedy')
    page.locator('#byokKey').fill(KEY)
    page.locator('#byokUse').click()
    expect(page.locator('#plannerChoice')).to_have_value('llm')
    page.locator('#plannerChoice').select_option('greedy')
    assert page.evaluate("IsnadKey.headers('/v1/verify')") == {'X-Isnad-Planner': 'greedy'}
    page.locator('.site-nav a[href="/console"]').click()
    page.wait_for_url('**/console')
    page.evaluate('() => IsnadKey.ready')
    expect(page.locator('#plannerChoice')).to_have_value('greedy')
    expect(page.locator('#byokState')).to_contain_text('Saved')
    page.locator('#plannerChoice').select_option('llm')
    assert page.evaluate("IsnadKey.headers('/v1/verify')") == {
        'X-Isnad-Planner': 'llm', 'X-Isnad-Gemini-Key': KEY,
    }


def test_lab_uses_site_key_without_requesting_a_personal_key(page, server):
    calls = []
    page.route('**/ui/settings.json', lambda route: route.fulfill(json={
        'accepts_request_key': True, 'server_gemini_available': True,
    }))
    page.goto(server + '/lab')
    page.evaluate('() => IsnadKey.ready')
    expect(page.locator('#byokState')).to_contain_text('Site Gemini key available')
    original = page.locator('#outDecision').inner_text()
    run = page.evaluate("() => JSON.parse(document.getElementById('bundleData').textContent).cases[0].run")
    run['planner_source'] = 'llm'
    run['outcome']['decision'] = 'DECLINE'

    def model_request(route):
        calls.append(route.request.headers)
        route.fulfill(json={'run': run, 'provider': 'mock', 'requested_planner': 'llm'})

    page.route('**/v1/lab/run/**', model_request)
    assert calls == []
    page.locator('#plannerChoice').select_option('llm')
    page.locator('#runLabLlm').click()
    expect(page.locator('#outDecision')).to_have_text('DECLINE')
    assert len(calls) == 1
    assert calls[0]['x-isnad-planner'] == 'llm'
    assert 'x-isnad-gemini-key' not in calls[0]
    expect(page.locator('#labModelStatus')).to_contain_text('Fresh Gemini-requested')
    page.locator('#showRecorded').click()
    expect(page.locator('#outDecision')).to_have_text(original)
