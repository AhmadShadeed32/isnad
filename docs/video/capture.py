import asyncio, os, sys, math
from playwright.async_api import async_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + BASE + "/scene.html"
FPS = 30

async def main():
    probe = "--probe" in sys.argv
    times = None
    if probe:
        times = [float(x) for x in sys.argv[sys.argv.index("--probe") + 1].split(",")]
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--force-color-profile=srgb",
                                          "--font-render-hinting=none",
                                          "--disable-lcd-text"])
        pg = await b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        await pg.goto(URL)
        await pg.wait_for_timeout(700)
        total = await pg.evaluate("window.TOTAL")
        if probe:
            os.makedirs(f"{BASE}/probe", exist_ok=True)
            for t in times:
                await pg.evaluate(f"window.setT({t})")
                await pg.wait_for_timeout(60)
                await pg.screenshot(path=f"{BASE}/probe/t{t:06.1f}.png")
            print("probes:", times)
        else:
            os.makedirs(f"{BASE}/frames", exist_ok=True)
            n = int(total * FPS)
            for i in range(n):
                await pg.evaluate(f"window.setT({i / FPS})")
                await pg.screenshot(path=f"{BASE}/frames/f{i:05d}.jpg",
                                    type="jpeg", quality=94)
                if i % 300 == 0:
                    print(f"{i}/{n}", flush=True)
            print("done", n)
        await b.close()

asyncio.run(main())
