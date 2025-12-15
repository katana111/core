const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

/**
 * Human-like Google Search using Puppeteer
 * Performs search, discovers page content, and extracts comprehensive results
 */

// Configuration
const CONFIG = {
    headless: false,
    query: process.argv[2] || "alternative data provider credit scoring",
    maxResults: 10,
    outputFile: 'google_search_results.json',
    humanLike: true,
};

// Helper: Random delay to simulate human behavior
const randomDelay = (min, max) => new Promise(r => setTimeout(r, Math.random() * (max - min) + min));

// Helper: Human-like typing
async function humanType(page, selector, text, options = {}) {
    const delay = options.delay || 100;
    const element = await page.$(selector);
    if (!element) throw new Error(`Element not found: ${selector}`);
    
    await element.click();
    await randomDelay(100, 300);
    
    for (const char of text) {
        await page.keyboard.type(char, { delay: Math.random() * delay + delay * 0.5 });
        await randomDelay(20, 80);
    }
}

// Helper: Scroll page like a human
async function humanScroll(page) {
    const scrollSteps = 3;
    for (let i = 0; i < scrollSteps; i++) {
        await page.evaluate(() => {
            window.scrollBy(0, window.innerHeight * 0.7);
        });
        await randomDelay(400, 800);
    }
    // Scroll back up a bit
    await page.evaluate(() => {
        window.scrollBy(0, -window.innerHeight * 0.3);
    });
    await randomDelay(200, 400);
}

// Main search function
async function performGoogleSearch() {
    console.log(`\n🔍 Starting Google Search for: "${CONFIG.query}"\n`);

    // Launch browser with human-like settings
    const browser = await puppeteer.launch({
        headless: CONFIG.headless,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--window-size=1366,900',
            '--lang=en-US,en'
        ],
        defaultViewport: {
            width: 1366,
            height: 900,
            deviceScaleFactor: 1,
        }
    });

    try {
        const page = await browser.newPage();

        // Stealth: Remove webdriver traces
        await page.evaluateOnNewDocument(() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        });

        // Set realistic user agent
        await page.setUserAgent(
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        );

        // Set additional headers
        await page.setExtraHTTPHeaders({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        });

        console.log('📱 Navigating to Google...');
        await page.goto('https://www.google.com/', { 
            waitUntil: 'networkidle2', 
            timeout: 60000 
        });
        await randomDelay(1000, 2000);

        // Handle cookie consent
        const consentSelectors = [
            'button#L2AGLb',
            'button[aria-label="Accept all"]',
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
        ];

        for (const selector of consentSelectors) {
            try {
                const button = await page.waitForSelector(selector, { timeout: 2000 });
                if (button) {
                    console.log('🍪 Handling cookie consent...');
                    await button.click();
                    await randomDelay(500, 1000);
                    break;
                }
            } catch (e) {
                // Continue to next selector
            }
        }

        // Find search input (multiple possible selectors)
        const searchSelectors = [
            'input[name="q"]',
            'textarea[name="q"]',
            'input[type="text"]',
            'input#input',
        ];

        let searchBox = null;
        for (const selector of searchSelectors) {
            try {
                await page.waitForSelector(selector, { timeout: 3000 });
                searchBox = selector;
                break;
            } catch (e) {
                continue;
            }
        }

        if (!searchBox) {
            throw new Error('Search box not found');
        }

        console.log('⌨️  Typing search query...');
        
        // Click search box
        await page.click(searchBox);
        await randomDelay(200, 400);
        
        // Clear existing text if any
        await page.keyboard.down('Control');
        await page.keyboard.press('a');
        await page.keyboard.up('Control');
        await randomDelay(100, 200);
        
        // Type query with human-like behavior
        await humanType(page, searchBox, CONFIG.query);

        await randomDelay(300, 600);
        console.log('🔎 Performing search...');

        // Submit search
        await page.keyboard.press('Enter');
        await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 });
        await randomDelay(1500, 2500);

        // Discover page structure
        console.log('🔍 Discovering page content...');
        const pageInfo = await page.evaluate(() => {
            const info = {
                url: window.location.href,
                title: document.title,
                hasSearchResults: !!document.querySelector('#search, div[data-async-context]'),
                resultContainers: [],
                allLinks: [],
            };

            // Find result containers
            const containers = document.querySelectorAll('#search, div[data-async-context], div#center_col');
            containers.forEach((container, idx) => {
                info.resultContainers.push({
                    id: container.id || `container-${idx}`,
                    className: container.className || '',
                    childCount: container.children.length,
                });
            });

            // Collect all links on page
            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                if (href && href.startsWith('http')) {
                    info.allLinks.push({
                        text: link.innerText?.substring(0, 100) || '',
                        href: href,
                    });
                }
            });

            return info;
        });

        console.log('\n📄 Page Discovery:');
        console.log(`   URL: ${pageInfo.url}`);
        console.log(`   Title: ${pageInfo.title}`);
        console.log(`   Has Results: ${pageInfo.hasSearchResults}`);
        console.log(`   Result Containers: ${pageInfo.resultContainers.length}`);
        console.log(`   Total Links: ${pageInfo.allLinks.length}\n`);

        // Scroll to load more content
        if (CONFIG.humanLike) {
            console.log('👆 Scrolling page (human-like)...');
            await humanScroll(page);
        }

        // Wait for results to fully load
        await page.waitForSelector('#search, div.g, div[data-async-context]', { timeout: 10000 });

        // Extract comprehensive search results
        console.log('📊 Extracting search results...');
        const results = await page.evaluate(() => {
            const items = [];
            const seenLinks = new Set();

            // Multiple selectors to catch different result layouts
            const resultSelectors = [
                'div#search div.g',
                'div#search div[data-ved]',
                'div[data-async-context] div.g',
                'div.rc',
                'div.r',
            ];

            let allResults = [];
            resultSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (!allResults.includes(el)) {
                        allResults.push(el);
                    }
                });
            });

            allResults.forEach((result, idx) => {
                try {
                    // Try multiple ways to extract link
                    const linkEl = result.querySelector('a[href^="http"]') || 
                                   result.querySelector('a[href*="http"]') ||
                                   result.closest('a[href^="http"]');
                    
                    const link = linkEl?.getAttribute('href') || 
                                linkEl?.href || 
                                result.querySelector('cite')?.textContent || '';

                    // Extract title
                    const titleEl = result.querySelector('h3') || 
                                   result.querySelector('a h3') ||
                                   result.querySelector('[role="heading"]');
                    const title = titleEl?.innerText?.trim() || titleEl?.textContent?.trim() || '';

                    // Extract snippet
                    const snippetSelectors = [
                        'div.VwiC3b',
                        'span[data-ved]',
                        'div.IsZvec',
                        'span.aCOpRe',
                    ];
                    let snippet = '';
                    for (const sel of snippetSelectors) {
                        const snippetEl = result.querySelector(sel);
                        if (snippetEl) {
                            snippet = snippetEl.innerText?.trim() || snippetEl.textContent?.trim() || '';
                            break;
                        }
                    }

                    // Extract display URL
                    const displayLinkEl = result.querySelector('cite') || 
                                         result.querySelector('span[style*="color"]');
                    const displayLink = displayLinkEl?.innerText?.trim() || 
                                       displayLinkEl?.textContent?.trim() || '';

                    // Clean and validate link
                    let cleanLink = link;
                    if (link.startsWith('/url?q=')) {
                        const urlMatch = link.match(/[?&]q=([^&]+)/);
                        if (urlMatch) {
                            cleanLink = decodeURIComponent(urlMatch[1]);
                        }
                    }

                    // Avoid duplicates and invalid entries
                    if (cleanLink && title && !seenLinks.has(cleanLink) && cleanLink.startsWith('http')) {
                        seenLinks.add(cleanLink);
                        items.push({
                            rank: idx + 1,
                            title: title,
                            link: cleanLink,
                            displayLink: displayLink || new URL(cleanLink).hostname,
                            snippet: snippet.substring(0, 200), // Limit snippet length
                            hasSnippet: !!snippet,
                        });
                    }
                } catch (e) {
                    // Skip malformed results
                    console.error(`Error extracting result ${idx}:`, e.message);
                }
            });

            return items;
        });

        // Limit results
        const limitedResults = results.slice(0, CONFIG.maxResults);

        // Display results
        console.log(`\n✅ Found ${limitedResults.length} results:\n`);
        limitedResults.forEach((result, i) => {
            console.log(`${i + 1}. ${result.title}`);
            console.log(`   🔗 ${result.link}`);
            if (result.displayLink) {
                console.log(`   📍 ${result.displayLink}`);
            }
            if (result.snippet) {
                console.log(`   📝 ${result.snippet.substring(0, 100)}...`);
            }
            console.log('');
        });

        // Save results to file
        const outputData = {
            query: CONFIG.query,
            timestamp: new Date().toISOString(),
            url: pageInfo.url,
            resultsCount: limitedResults.length,
            pageInfo: pageInfo,
            results: limitedResults,
        };

        const outputPath = path.join(__dirname, CONFIG.outputFile);
        fs.writeFileSync(outputPath, JSON.stringify(outputData, null, 2), 'utf8');
        console.log(`💾 Results saved to: ${outputPath}\n`);

        // Keep browser open briefly for inspection
        if (!CONFIG.headless) {
            console.log('👀 Keeping browser open for 5 seconds for inspection...');
            await new Promise(r => setTimeout(r, 5000));
        }

        return outputData;

    } catch (error) {
        console.error('\n❌ Error during search:', error.message);
        throw error;
    } finally {
        await browser.close();
    }
}

// Run the search
performGoogleSearch()
    .then(() => {
        console.log('\n✨ Search completed successfully!\n');
        process.exit(0);
    })
    .catch((error) => {
        console.error('\n💥 Search failed:', error);
        process.exit(1);
    });
