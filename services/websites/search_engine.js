const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

/**
 * Focused Website Scraper using Puppeteer
 * Extracts: texts (with summaries), social media, job postings, 
 * addresses, compliance info (ISO/SOC2/GDPR), team members, pricing,
 * blog posts, news articles (with summaries)
 */

// Configuration
const CONFIG = {
    headless: true,
    timeout: 30000,
    outputFile: 'website_scrape_results.json',
    blogOutputFile: 'blog_posts_summaries.json',
    aiAnalysisFile: 'website_ai_analysis.json',
    waitFor: 'networkidle2',
    humanLike: true,
    maxBlogPosts: 50, // Maximum number of blog posts to scrape
    maxPostLength: 5000, // Maximum characters per post to summarize
    followLinks: true, // Follow important links (Careers, Pricing, etc.)
    maxPagesToFollow: 10, // Maximum number of additional pages to scrape
    followBlogPagination: true, // Follow pagination links for blog posts
    maxBlogPages: 5, // Maximum number of blog listing pages to visit
    useAIProcessor: true, // Enable AI processing with processor.py
    aiProcessorPath: null, // Path to processor.py (auto-detected if null)
    // Summarization service endpoint (if using external service)
    summarizeEndpoint: null, // Set to your LLM service endpoint if available
};

// Helper: Random delay for human-like behavior
const randomDelay = (min, max) => 
    new Promise(r => setTimeout(r, Math.random() * (max - min) + min));

// Helper: Clean text
function cleanText(text) {
    if (!text) return '';
    return text.replace(/\s+/g, ' ').trim();
}

// Helper: Check if URL is a blog post/article
function isBlogPost(url, pathname) {
    const blogIndicators = [
        '/blog/', '/posts/', '/article/', '/news/', '/press/', 
        '/journal/', '/updates/', '/archive/', '/category/', 
        '/tag/', '/author/', '/date/', '/2024/', '/2023/', '/2022/',
        '/story/', '/post/', '/read/', '/content/'
    ];
    
    const lowerUrl = url.toLowerCase();
    const lowerPath = pathname.toLowerCase();
    
    return blogIndicators.some(indicator => 
        lowerUrl.includes(indicator) || lowerPath.includes(indicator)
    );
}

// Helper: Scrape individual blog post/article
async function scrapeBlogPost(page, postUrl, browser) {
    try {
        console.log(`  📰 Scraping: ${postUrl}`);
        
        const postPage = await browser.newPage();
        await postPage.goto(postUrl, { 
            waitUntil: CONFIG.waitFor, 
            timeout: CONFIG.timeout 
        });
        
        await randomDelay(1000, 2000);
        
        const postData = await postPage.evaluate(() => {
            const data = {
                url: window.location.href,
                title: '',
                author: '',
                date: '',
                content: '',
                excerpt: '',
                tags: [],
                categories: [],
            };
            
            // Extract title
            const titleSelectors = [
                'h1',
                'article h1',
                '[class*="title"]',
                '[class*="post-title"]',
                '[class*="article-title"]',
            ];
            
            for (const selector of titleSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    data.title = (el.innerText || el.textContent || '').trim();
                    break;
                }
            }
            
            // Extract author
            const authorSelectors = [
                '[class*="author"]',
                '[rel="author"]',
                '[itemprop="author"]',
                '.byline',
            ];
            
            for (const selector of authorSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    data.author = (el.innerText || el.textContent || '').trim();
                    break;
                }
            }
            
            // Extract date
            const dateSelectors = [
                'time[datetime]',
                '[class*="date"]',
                '[class*="published"]',
                '[itemprop="datePublished"]',
            ];
            
            for (const selector of dateSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    const datetime = el.getAttribute('datetime') || 
                                   el.getAttribute('content') ||
                                   (el.innerText || el.textContent || '').trim();
                    data.date = datetime;
                    break;
                }
            }
            
            // Extract main content
            const contentSelectors = [
                'article',
                '[class*="post-content"]',
                '[class*="article-content"]',
                '[class*="entry-content"]',
                'main',
                '[role="article"]',
            ];
            
            let contentElement = null;
            for (const selector of contentSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    contentElement = el;
                    break;
                }
            }
            
            if (contentElement) {
                // Remove unwanted elements
                const clone = contentElement.cloneNode(true);
                ['script', 'style', 'nav', 'aside', 'footer', 'header'].forEach(tag => {
                    clone.querySelectorAll(tag).forEach(el => el.remove());
                });
                
                data.content = (clone.innerText || clone.textContent || '').trim();
            } else {
                // Fallback: get body content
                const bodyClone = document.body.cloneNode(true);
                ['script', 'style', 'nav', 'aside', 'footer', 'header'].forEach(tag => {
                    bodyClone.querySelectorAll(tag).forEach(el => el.remove());
                });
                data.content = (bodyClone.innerText || bodyClone.textContent || '').trim();
            }
            
            // Extract excerpt/description
            const excerptSelectors = [
                '[class*="excerpt"]',
                '[class*="summary"]',
                'meta[property="og:description"]',
                'meta[name="description"]',
            ];
            
            for (const selector of excerptSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    data.excerpt = el.getAttribute('content') || 
                                  (el.innerText || el.textContent || '').trim();
                    break;
                }
            }
            
            // Extract tags
            document.querySelectorAll('[class*="tag"], [rel="tag"], .tags a').forEach(el => {
                const tag = (el.innerText || el.textContent || '').trim();
                if (tag && !data.tags.includes(tag)) {
                    data.tags.push(tag);
                }
            });
            
            // Extract categories
            document.querySelectorAll('[class*="categor"], .categories a, [rel="category"]').forEach(el => {
                const cat = (el.innerText || el.textContent || '').trim();
                if (cat && !data.categories.includes(cat)) {
                    data.categories.push(cat);
                }
            });
            
            return data;
        });
        
        await postPage.close();
        
        // Limit content length
        if (postData.content.length > CONFIG.maxPostLength) {
            postData.content = postData.content.substring(0, CONFIG.maxPostLength) + '...';
        }
        
        // Create summary using AI processor
        postData.summary = await summarizeWithModel(
            postData.excerpt || postData.content.substring(0, 1000)
        );
        
        postData.wordCount = postData.content.split(/\s+/).filter(w => w.length > 0).length;
        postData.scrapedAt = new Date().toISOString();
        
        return postData;
        
    } catch (error) {
        console.error(`  ❌ Error scraping post ${postUrl}:`, error.message);
        return null;
    }
}

// Helper: Simple text summarization (can be replaced with LLM call)
async function summarizeText(text, maxLength = 200) {
    if (!text || text.length <= maxLength) return text;
    
    // Simple extractive summarization - take first sentences
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [];
    let summary = '';
    
    for (const sentence of sentences) {
        if (summary.length + sentence.length <= maxLength) {
            summary += sentence;
        } else {
            break;
        }
    }
    
    return summary || text.substring(0, maxLength) + '...';
}

// Helper: Call Python processor for analysis and summarization
async function processWithAI(text, taskType = 'summarize', maxTokens = 200) {
    if (!text || text.trim().length === 0) {
        return text;
    }
    
    // Check if AI processing is enabled
    if (!CONFIG.useAIProcessor) {
        return await summarizeText(text);
    }
    
    // Limit text length to avoid token limits
    const maxTextLength = 3000;
    const textToProcess = text.length > maxTextLength ? text.substring(0, maxTextLength) + '...' : text;
    
    try {
        // Get processor script path
        const processorPath = CONFIG.aiProcessorPath || path.join(__dirname, '../ai/processor.py');
        
        // Check if processor exists
        if (!fs.existsSync(processorPath)) {
            console.warn(`AI processor not found at ${processorPath}, using fallback summarization`);
            return await summarizeText(textToProcess);
        }
        
        // Create a temporary file to pass text (more reliable than command line)
        const tempFile = path.join(__dirname, `temp_input_${Date.now()}.txt`);
        fs.writeFileSync(tempFile, textToProcess, 'utf8');
        
        // Build command with proper escaping and quiet mode
        const command = `python3 "${processorPath}" --file "${tempFile}" --task "${taskType}" --max-tokens ${maxTokens} --quiet`;
        
        const { stdout, stderr } = await execAsync(command, {
            maxBuffer: 10 * 1024 * 1024, // 10MB buffer
            timeout: 30000, // 30 second timeout
        });
        
        // Clean up temp file
        try {
            if (fs.existsSync(tempFile)) {
                fs.unlinkSync(tempFile);
            }
        } catch (cleanupError) {
            // Ignore cleanup errors
        }
        
        // Filter out model loading messages from stderr
        if (stderr && !stderr.includes('Warning') && !stderr.includes('Loading') && !stderr.includes('Model')) {
            console.warn(`Processor warning: ${stderr.substring(0, 200)}`);
        }
        
        // Extract just the response (remove any verbose output)
        const lines = stdout.trim().split('\n');
        const result = lines[lines.length - 1].trim(); // Get last line which should be the response
        
        // If result looks valid, return it; otherwise fall back to simple summary
        if (result && result.length > 10 && !result.includes('Error:')) {
            return result;
        } else {
            return await summarizeText(textToProcess);
        }
        
    } catch (error) {
        console.warn(`AI processing failed: ${error.message}, using fallback summarization`);
        return await summarizeText(textToProcess);
    }
}

// Helper: Call Python LLM service for better summarization
async function summarizeWithModel(text) {
    return await processWithAI(text, 'summarize', 200);
}

// Helper: Analyze text with AI
async function analyzeWithAI(text) {
    return await processWithAI(text, 'analyze', 300);
}

// Helper: Process JSON data through AI processor
async function processDataWithAI(data) {
    // Check if AI processing is enabled
    if (!CONFIG.useAIProcessor) {
        console.log('⚠️  AI processing disabled, skipping AI analysis');
        return {
            ...data,
            aiAnalysis: {
                timestamp: new Date().toISOString(),
                enabled: false,
                message: 'AI processing disabled in configuration',
            }
        };
    }
    
    console.log('🤖 Processing data with AI processor...');
    
    const processedData = {
        ...data,
        aiAnalysis: {
            timestamp: new Date().toISOString(),
            enabled: true,
            summaries: {},
            analyses: {},
        }
    };
    
    try {
        // Process text sections
        if (data.texts && data.texts.sections) {
            console.log(`  📝 Processing ${data.texts.sections.length} text sections...`);
            const sectionSummaries = [];
            for (let i = 0; i < data.texts.sections.length; i++) {
                const section = data.texts.sections[i];
                if (section.text && section.text.length > 100) {
                    const summary = await processWithAI(section.text, 'summarize', 200);
                    sectionSummaries.push({
                        index: i,
                        summary: summary,
                    });
                }
            }
            processedData.aiAnalysis.summaries.textSections = sectionSummaries;
        }
        
        // Process banners
        if (data.banners && data.banners.length > 0) {
            console.log(`  🎯 Processing ${data.banners.length} banners...`);
            const bannerAnalyses = [];
            for (let i = 0; i < data.banners.length; i++) {
                const banner = data.banners[i];
                if (banner.text && banner.text.length > 50) {
                    const analysis = await processWithAI(banner.text, 'analyze', 150);
                    bannerAnalyses.push({
                        index: i,
                        analysis: analysis,
                        mainHeading: banner.headings.length > 0 ? banner.headings[0].text : null,
                    });
                }
            }
            processedData.aiAnalysis.analyses.banners = bannerAnalyses;
        }
        
        // Process pricing information
        if (data.pricing && data.pricing.length > 0) {
            console.log(`  💰 Processing pricing information...`);
            const pricingAnalyses = [];
            for (let i = 0; i < data.pricing.length; i++) {
                const pricing = data.pricing[i];
                const pricingText = typeof pricing === 'string' ? pricing : 
                                   pricing.text || JSON.stringify(pricing);
                if (pricingText && pricingText.length > 50) {
                    const analysis = await processWithAI(pricingText, 'analyze', 200);
                    pricingAnalyses.push({
                        index: i,
                        analysis: analysis,
                        extractedPrices: pricing.prices || [],
                    });
                }
            }
            processedData.aiAnalysis.analyses.pricing = pricingAnalyses;
        }
        
        // Process team members
        if (data.teamMembers && data.teamMembers.length > 0) {
            console.log(`  👥 Processing team information...`);
            const teamSummary = data.teamMembers.map(m => 
                `${m.name || 'Unknown'}: ${m.role || 'N/A'} - ${(m.bio || '').substring(0, 100)}`
            ).join('\n');
            if (teamSummary.length > 50) {
                processedData.aiAnalysis.summaries.team = await processWithAI(teamSummary, 'summarize', 150);
            }
        }
        
        // Process compliance information
        if (data.compliance) {
            console.log(`  ✅ Processing compliance information...`);
            const complianceText = [];
            if (data.compliance.iso && data.compliance.iso.length > 0) {
                complianceText.push(`ISO: ${data.compliance.iso.map(c => c.context || c.keyword).join('; ')}`);
            }
            if (data.compliance.soc2 && data.compliance.soc2.length > 0) {
                complianceText.push(`SOC2: ${data.compliance.soc2.map(c => c.context || c.keyword).join('; ')}`);
            }
            if (data.compliance.gdpr && data.compliance.gdpr.length > 0) {
                complianceText.push(`GDPR: ${data.compliance.gdpr.map(c => c.context || c.keyword).join('; ')}`);
            }
            if (complianceText.length > 0) {
                processedData.aiAnalysis.analyses.compliance = await processWithAI(
                    complianceText.join('\n'), 
                    'analyze', 
                    200
                );
            }
        }
        
        // Process blog posts summaries
        if (data.blogPosts && data.blogPosts.length > 0) {
            console.log(`  📰 Processing ${data.blogPosts.length} blog posts...`);
            // Blog posts already have summaries, but we can enhance them
            for (let i = 0; i < Math.min(data.blogPosts.length, 5); i++) {
                const post = data.blogPosts[i];
                if (post.content && post.content.length > 200) {
                    const enhancedSummary = await processWithAI(post.content, 'summarize', 150);
                    if (enhancedSummary && enhancedSummary.length > 20) {
                        post.aiEnhancedSummary = enhancedSummary;
                    }
                }
            }
        }
        
        // Create overall summary
        console.log('  📊 Creating overall website analysis...');
        const overallText = [
            `Website: ${data.domain || 'Unknown'}`,
            `Main content sections: ${data.texts?.sections?.length || 0}`,
            `Banners: ${data.banners?.length || 0}`,
            `Team members: ${data.teamMembers?.length || 0}`,
            `Pricing plans: ${data.pricing?.length || 0}`,
            `Blog posts: ${data.blogPosts?.length || 0}`,
        ].join('\n');
        
        processedData.aiAnalysis.overallSummary = await processWithAI(
            overallText, 
            'summarize', 
            200
        );
        
        console.log('✅ AI processing completed!\n');
        
    } catch (error) {
        console.error(`❌ Error during AI processing: ${error.message}`);
        processedData.aiAnalysis.error = error.message;
    }
    
    return processedData;
}

// Helper: Discover important links (Careers, Pricing, About, etc.)
async function discoverImportantLinks(page, baseUrl) {
    const importantKeywords = [
        'career', 'careers', 'jobs', 'hiring', 'join', 'team',
        'pricing', 'price', 'plan', 'plans', 'subscription', 'cost',
        'about', 'about us', 'company', 'team', 'leadership',
        'contact', 'contact us', 'get in touch',
        'product', 'products', 'solutions', 'services',
        'security', 'compliance', 'trust', 'certification',
    ];

    const links = await page.evaluate((baseUrlString, keywords) => {
        const foundLinks = [];
        const seenUrls = new Set();
        const baseDomain = new URL(baseUrlString).hostname;

        document.querySelectorAll('a[href]').forEach(link => {
            const href = link.getAttribute('href');
            if (!href) return;

            try {
                const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                const urlObj = new URL(fullUrl);
                
                // Only internal links
                if (urlObj.hostname !== baseDomain) return;
                
                // Skip if already seen or if it's a blog post
                if (seenUrls.has(fullUrl)) return;
                
                const linkText = (link.innerText || link.textContent || '').toLowerCase().trim();
                const pathname = urlObj.pathname.toLowerCase();
                
                // Check if link text or URL contains important keywords
                const isImportant = keywords.some(keyword => 
                    linkText.includes(keyword) || pathname.includes(keyword)
                );
                
                if (isImportant && fullUrl !== baseUrlString && !fullUrl.includes('#') && !fullUrl.includes('mailto:')) {
                    seenUrls.add(fullUrl);
                    foundLinks.push({
                        url: fullUrl,
                        text: (link.innerText || link.textContent || '').trim(),
                        type: keywords.find(k => linkText.includes(k) || pathname.includes(k)) || 'other',
                    });
                }
            } catch {}
        });

        return foundLinks;
    }, baseUrl.href, importantKeywords);

    // Group by type and limit
    const grouped = {};
    links.forEach(link => {
        if (!grouped[link.type]) grouped[link.type] = [];
        grouped[link.type].push(link);
    });

    // Select top links from each category
    const selected = [];
    Object.keys(grouped).forEach(type => {
        grouped[type].slice(0, 2).forEach(link => selected.push(link));
    });

    return selected.slice(0, CONFIG.maxPagesToFollow);
}

// Helper: Scrape additional page
async function scrapeAdditionalPage(page, pageUrl, browser, pageType) {
    try {
        console.log(`  📄 Scraping ${pageType} page: ${pageUrl}`);
        
        const newPage = await browser.newPage();
        await newPage.goto(pageUrl, { 
            waitUntil: CONFIG.waitFor, 
            timeout: CONFIG.timeout 
        });
        
        await randomDelay(1000, 2000);
        
        // Scroll to load content
        if (CONFIG.humanLike) {
            await newPage.evaluate(async () => {
                for (let i = 0; i < 2; i++) {
                    window.scrollBy(0, window.innerHeight * 0.7);
                    await new Promise(r => setTimeout(r, 300));
                }
            });
        }

        const pageData = await newPage.evaluate((baseUrlString) => {
            const data = {
                url: window.location.href,
                title: document.title || '',
                content: '',
                headings: [],
                links: [],
                banners: [],
            };

            // Extract main content
            const contentSelectors = [
                'main',
                'article',
                '[role="main"]',
                '#content',
                '.content',
                '.main-content',
            ];

            let contentElement = null;
            for (const selector of contentSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    contentElement = el;
                    break;
                }
            }

            if (contentElement) {
                const clone = contentElement.cloneNode(true);
                ['script', 'style', 'nav', 'aside', 'footer', 'header'].forEach(tag => {
                    clone.querySelectorAll(tag).forEach(el => el.remove());
                });
                data.content = (clone.innerText || clone.textContent || '').trim();
            } else {
                const bodyClone = document.body.cloneNode(true);
                ['script', 'style', 'nav', 'aside', 'footer', 'header'].forEach(tag => {
                    bodyClone.querySelectorAll(tag).forEach(el => el.remove());
                });
                data.content = (bodyClone.innerText || bodyClone.textContent || '').trim();
            }

            // Extract headings
            ['h1', 'h2', 'h3'].forEach(tag => {
                document.querySelectorAll(tag).forEach(heading => {
                    const text = (heading.innerText || heading.textContent || '').trim();
                    if (text) {
                        data.headings.push({
                            level: tag,
                            text: text,
                        });
                    }
                });
            });

            // Extract important links
            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                const text = (link.innerText || link.textContent || '').trim();
                if (href && text && href.startsWith('http')) {
                    data.links.push({
                        url: href,
                        text: text.substring(0, 100),
                    });
                }
            });

            // Extract banners (same logic as main page)
            const bannerSelectors = [
                '.web-top-banner-container',
                '.top-banner',
                '.banner',
                '.hero',
                '.hero-banner',
                '.header-banner',
                '[class*="banner"]',
                '[class*="hero"]',
                '[id*="banner"]',
                '[id*="hero"]',
                '[role="banner"]',
                '[class*="top-banner"]',
                '[id*="top-banner"]',
            ];

            bannerSelectors.forEach(selector => {
                try {
                    document.querySelectorAll(selector).forEach(banner => {
                        const rect = banner.getBoundingClientRect();
                        if (rect.height < 50 && rect.width < 200) return;
                        
                        const bannerClone = banner.cloneNode(true);
                        ['script', 'style'].forEach(tag => {
                            bannerClone.querySelectorAll(tag).forEach(el => el.remove());
                        });

                        const bannerData = {
                            selector: selector,
                            className: banner.className || '',
                            id: banner.id || '',
                            text: (bannerClone.innerText || bannerClone.textContent || '').trim(),
                            html: banner.innerHTML.substring(0, 1000),
                            position: {
                                top: rect.top,
                                left: rect.left,
                                width: rect.width,
                                height: rect.height,
                            },
                            headings: [],
                            links: [],
                            images: [],
                            buttons: [],
                        };

                        banner.querySelectorAll('h1, h2, h3').forEach(heading => {
                            const text = (heading.innerText || heading.textContent || '').trim();
                            if (text) {
                                bannerData.headings.push({
                                    level: heading.tagName.toLowerCase(),
                                    text: text,
                                });
                            }
                        });

                        banner.querySelectorAll('a[href]').forEach(link => {
                            const href = link.getAttribute('href');
                            const text = (link.innerText || link.textContent || '').trim();
                            if (href) {
                                try {
                                    const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                                    bannerData.links.push({
                                        url: fullUrl,
                                        text: text.substring(0, 100),
                                    });
                                } catch {}
                            }
                        });

                        banner.querySelectorAll('img').forEach(img => {
                            const src = img.getAttribute('src') || img.getAttribute('data-src') || '';
                            if (src) {
                                try {
                                    const fullUrl = src.startsWith('http') ? src : new URL(src, baseUrlString).href;
                                    bannerData.images.push({
                                        url: fullUrl,
                                        alt: img.getAttribute('alt') || '',
                                    });
                                } catch {}
                            }
                        });

                        if (bannerData.text.length > 20 || bannerData.headings.length > 0 || bannerData.images.length > 0) {
                            data.banners.push(bannerData);
                        }
                    });
                } catch {}
            });

            return data;
        }, pageUrl);

        await newPage.close();

        // Create summary using AI processor
        if (pageData.content && pageData.content.length > 100) {
            pageData.summary = await summarizeWithModel(
                pageData.content.substring(0, 2000)
            );
        }
        pageData.wordCount = pageData.content.split(/\s+/).filter(w => w.length > 0).length;
        pageData.scrapedAt = new Date().toISOString();
        pageData.pageType = pageType;

        return pageData;

    } catch (error) {
        console.error(`  ❌ Error scraping page ${pageUrl}:`, error.message);
        return null;
    }
}

// Helper: Find blog pagination links
async function findBlogPaginationLinks(page, baseUrl) {
    const paginationLinks = await page.evaluate((baseUrlString) => {
        const links = [];
        const baseDomain = new URL(baseUrlString).hostname;

        // Common pagination patterns
        const paginationSelectors = [
            'a[rel="next"]',
            '.pagination a',
            '.pager a',
            '[class*="pagination"] a',
            '[class*="pager"] a',
            '[class*="next"]',
            '[class*="page"] a',
            'a[aria-label*="next"]',
            'a[aria-label*="Next"]',
            'a:contains("Next")',
            'a:contains("next")',
        ];

        paginationSelectors.forEach(selector => {
            try {
                document.querySelectorAll(selector).forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href) return;

                    try {
                        const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                        const urlObj = new URL(fullUrl);
                        
                        if (urlObj.hostname === baseDomain) {
                            const linkText = (link.innerText || link.textContent || '').toLowerCase();
                            if (linkText.includes('next') || linkText.includes('more') || 
                                link.getAttribute('rel') === 'next' ||
                                link.getAttribute('aria-label')?.toLowerCase().includes('next')) {
                                links.push({
                                    url: fullUrl,
                                    text: (link.innerText || link.textContent || '').trim(),
                                });
                            }
                        }
                    } catch {}
                });
            } catch {}
        });

        // Also check for numbered pagination
        document.querySelectorAll('a').forEach(link => {
            const href = link.getAttribute('href');
            const text = (link.innerText || link.textContent || '').trim();
            const hrefLower = href?.toLowerCase() || '';
            
            // Check for page numbers in URL or text
            if (href && (hrefLower.includes('/page/') || hrefLower.includes('?page=') || 
                /^page\s*\d+$/i.test(text) || /^\d+$/.test(text))) {
                try {
                    const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                    const urlObj = new URL(fullUrl);
                    if (urlObj.hostname === baseDomain && !links.find(l => l.url === fullUrl)) {
                        links.push({
                            url: fullUrl,
                            text: text,
                        });
                    }
                } catch {}
            }
        });

        return links;
    }, baseUrl.href);

    return paginationLinks;
}

// Main scraping function
async function scrapeWebsite(targetUrl) {
    if (!targetUrl || !targetUrl.startsWith('http')) {
        throw new Error('Please provide a valid URL starting with http:// or https://');
    }

    console.log(`\n🌐 Scraping website: ${targetUrl}\n`);

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
        const baseUrl = new URL(targetUrl);

        // Stealth mode
        await page.evaluateOnNewDocument(() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        });

        await page.setUserAgent(
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        );

        await page.setExtraHTTPHeaders({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'DNT': '1',
        });

        console.log('📡 Loading page...');
        await page.goto(targetUrl, { 
            waitUntil: CONFIG.waitFor, 
            timeout: CONFIG.timeout 
        });

        if (CONFIG.humanLike) {
            await randomDelay(1000, 2000);
            await page.evaluate(async () => {
                for (let i = 0; i < 2; i++) {
                    window.scrollBy(0, window.innerHeight * 0.7);
                    await new Promise(r => setTimeout(r, 300));
                }
            });
        }

        console.log('🔍 Extracting focused information...');
        
        // Extract only the requested information
        const scrapedData = await page.evaluate((baseUrlString) => {
            // Helper function to check if URL is a blog post
            function checkIsBlogPost(url, pathname) {
                const blogIndicators = [
                    '/blog/', '/posts/', '/article/', '/news/', '/press/', 
                    '/journal/', '/updates/', '/archive/', '/category/', 
                    '/tag/', '/author/', '/date/', '/2024/', '/2023/', '/2022/',
                    '/story/', '/post/', '/read/', '/content/'
                ];
                
                const lowerUrl = url.toLowerCase();
                const lowerPath = pathname.toLowerCase();
                
                return blogIndicators.some(indicator => 
                    lowerUrl.includes(indicator) || lowerPath.includes(indicator)
                );
            }

            const data = {
                texts: [],
                banners: [],
                socialMedia: {},
                jobPostings: [],
                addresses: {
                    email: [],
                    physical: [],
                },
                compliance: {
                    iso: [],
                    soc2: [],
                    gdpr: [],
                    other: [],
                },
                teamMembers: [],
                pricing: [],
            };

            const baseUrl = new URL(baseUrlString);
            const baseDomain = baseUrl.hostname;

            // ===== TEXTS (main content, excluding individual blog post pages) =====
            const textSections = [];
            const headings = [];
            
            // Get main content areas (but skip if we're on a blog post page itself)
            const isBlogPostPage = checkIsBlogPost(window.location.href, window.location.pathname);
            
            if (!isBlogPostPage) {
                const mainSelectors = [
                    'main',
                    'article',
                    '[role="main"]',
                    '#content',
                    '.content',
                    '.main-content',
                    'section',
                ];

                mainSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(element => {
                        const text = element.innerText?.trim() || element.textContent?.trim();
                        if (text && text.length > 50) {
                            textSections.push({
                                text: text,
                                section: selector,
                                wordCount: text.split(/\s+/).filter(w => w.length > 0).length,
                            });
                        }
                    });
                });

                // Also get headings for context
                ['h1', 'h2', 'h3'].forEach(tag => {
                    document.querySelectorAll(tag).forEach(heading => {
                        const text = heading.innerText?.trim() || heading.textContent?.trim();
                        if (text) {
                            headings.push({
                                level: tag,
                                text: text,
                            });
                        }
                    });
                });
            }

            data.texts = {
                sections: textSections,
                headings: headings,
            };

            // ===== TOP BANNERS =====
            const banners = [];
            
            // Common banner selectors
            const bannerSelectors = [
                '.web-top-banner-container',
                '.top-banner',
                '.banner',
                '.hero',
                '.hero-banner',
                '.header-banner',
                '.page-banner',
                '.section-banner',
                '[class*="banner"]',
                '[class*="hero"]',
                '[id*="banner"]',
                '[id*="hero"]',
                '[role="banner"]',
                'section[class*="banner"]',
                'div[class*="banner"]',
                '.jumbotron',
                '.cta-banner',
                '.promo-banner',
                '.announcement-banner',
            ];

            bannerSelectors.forEach(selector => {
                try {
                    document.querySelectorAll(selector).forEach(banner => {
                        // Skip if banner is too small (likely not a main banner)
                        const rect = banner.getBoundingClientRect();
                        if (rect.height < 50 && rect.width < 200) return;
                        
                        // Extract banner content
                        const bannerClone = banner.cloneNode(true);
                        ['script', 'style'].forEach(tag => {
                            bannerClone.querySelectorAll(tag).forEach(el => el.remove());
                        });

                        const bannerData = {
                            selector: selector,
                            className: banner.className || '',
                            id: banner.id || '',
                            text: (bannerClone.innerText || bannerClone.textContent || '').trim(),
                            html: banner.innerHTML.substring(0, 1000), // Limit HTML length
                            position: {
                                top: rect.top,
                                left: rect.left,
                                width: rect.width,
                                height: rect.height,
                            },
                            headings: [],
                            links: [],
                            images: [],
                            buttons: [],
                            attributes: {},
                        };

                        // Extract headings from banner
                        banner.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
                            const text = (heading.innerText || heading.textContent || '').trim();
                            if (text) {
                                bannerData.headings.push({
                                    level: heading.tagName.toLowerCase(),
                                    text: text,
                                });
                            }
                        });

                        // Extract links from banner
                        banner.querySelectorAll('a[href]').forEach(link => {
                            const href = link.getAttribute('href');
                            const text = (link.innerText || link.textContent || '').trim();
                            if (href) {
                                try {
                                    const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                                    bannerData.links.push({
                                        url: fullUrl,
                                        text: text.substring(0, 100),
                                        target: link.getAttribute('target') || null,
                                    });
                                } catch {
                                    bannerData.links.push({
                                        url: href,
                                        text: text.substring(0, 100),
                                        target: link.getAttribute('target') || null,
                                    });
                                }
                            }
                        });

                        // Extract images from banner
                        banner.querySelectorAll('img').forEach(img => {
                            const src = img.getAttribute('src') || img.getAttribute('data-src') || '';
                            if (src) {
                                try {
                                    const fullUrl = src.startsWith('http') ? src : new URL(src, baseUrlString).href;
                                    bannerData.images.push({
                                        url: fullUrl,
                                        alt: img.getAttribute('alt') || '',
                                        title: img.getAttribute('title') || null,
                                    });
                                } catch {
                                    bannerData.images.push({
                                        url: src,
                                        alt: img.getAttribute('alt') || '',
                                        title: img.getAttribute('title') || null,
                                    });
                                }
                            }
                        });

                        // Extract buttons/CTAs from banner
                        banner.querySelectorAll('button, [role="button"], a[class*="button"], a[class*="btn"], input[type="submit"], input[type="button"]').forEach(btn => {
                            const text = (btn.innerText || btn.textContent || btn.value || '').trim();
                            if (text) {
                                bannerData.buttons.push({
                                    text: text,
                                    type: btn.tagName.toLowerCase(),
                                    href: btn.getAttribute('href') || null,
                                    className: btn.className || '',
                                });
                            }
                        });

                        // Extract data attributes and other important attributes
                        Array.from(banner.attributes).forEach(attr => {
                            if (attr.name.startsWith('data-') || 
                                ['id', 'class', 'role', 'aria-label', 'aria-labelledby'].includes(attr.name)) {
                                bannerData.attributes[attr.name] = attr.value;
                            }
                        });

                        // Only add if banner has meaningful content
                        if (bannerData.text.length > 20 || bannerData.headings.length > 0 || bannerData.images.length > 0) {
                            banners.push(bannerData);
                        }
                    });
                } catch (e) {
                    // Continue if selector fails
                }
            });

            // Also check for banner-like sections at the top of the page
            const topSections = document.querySelectorAll('section, div[class], header');
            topSections.forEach(section => {
                const rect = section.getBoundingClientRect();
                // Check if section is at the top of viewport and reasonably sized
                if (rect.top >= 0 && rect.top < 500 && rect.height > 100 && rect.width > 300) {
                    const className = section.className || '';
                    const id = section.id || '';
                    const hasBannerIndicators = 
                        className.toLowerCase().includes('banner') ||
                        className.toLowerCase().includes('hero') ||
                        id.toLowerCase().includes('banner') ||
                        id.toLowerCase().includes('hero') ||
                        section.getAttribute('role') === 'banner';

                    if (hasBannerIndicators && !banners.find(b => b.id === id || b.className === className)) {
                        const sectionClone = section.cloneNode(true);
                        ['script', 'style'].forEach(tag => {
                            sectionClone.querySelectorAll(tag).forEach(el => el.remove());
                        });

                        const bannerData = {
                            selector: 'top-section',
                            className: className,
                            id: id,
                            text: (sectionClone.innerText || sectionClone.textContent || '').trim(),
                            html: section.innerHTML.substring(0, 1000),
                            position: {
                                top: rect.top,
                                left: rect.left,
                                width: rect.width,
                                height: rect.height,
                            },
                            headings: [],
                            links: [],
                            images: [],
                            buttons: [],
                            attributes: {},
                        };

                        // Extract same data as above
                        section.querySelectorAll('h1, h2, h3').forEach(heading => {
                            const text = (heading.innerText || heading.textContent || '').trim();
                            if (text) {
                                bannerData.headings.push({
                                    level: heading.tagName.toLowerCase(),
                                    text: text,
                                });
                            }
                        });

                        section.querySelectorAll('a[href]').forEach(link => {
                            const href = link.getAttribute('href');
                            const text = (link.innerText || link.textContent || '').trim();
                            if (href) {
                                try {
                                    const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                                    bannerData.links.push({
                                        url: fullUrl,
                                        text: text.substring(0, 100),
                                    });
                                } catch {}
                            }
                        });

                        section.querySelectorAll('img').forEach(img => {
                            const src = img.getAttribute('src') || img.getAttribute('data-src') || '';
                            if (src) {
                                try {
                                    const fullUrl = src.startsWith('http') ? src : new URL(src, baseUrlString).href;
                                    bannerData.images.push({
                                        url: fullUrl,
                                        alt: img.getAttribute('alt') || '',
                                    });
                                } catch {}
                            }
                        });

                        if (bannerData.text.length > 20 || bannerData.headings.length > 0) {
                            banners.push(bannerData);
                        }
                    }
                }
            });

            data.banners = banners;

            // ===== SOCIAL MEDIA LINKS =====
            const socialDomains = {
                facebook: ['facebook.com', 'fb.com'],
                twitter: ['twitter.com', 'x.com'],
                linkedin: ['linkedin.com'],
                instagram: ['instagram.com'],
                youtube: ['youtube.com', 'youtu.be'],
                github: ['github.com'],
                pinterest: ['pinterest.com'],
                tiktok: ['tiktok.com'],
                reddit: ['reddit.com'],
                discord: ['discord.gg', 'discord.com'],
                slack: ['slack.com'],
                medium: ['medium.com'],
            };

            Object.keys(socialDomains).forEach(platform => {
                data.socialMedia[platform] = [];
            });

            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                if (!href) return;

                try {
                    const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                    const linkDomain = new URL(fullUrl).hostname.toLowerCase();
                    
                    Object.keys(socialDomains).forEach(platform => {
                        if (socialDomains[platform].some(domain => linkDomain.includes(domain))) {
                            data.socialMedia[platform].push({
                                url: fullUrl,
                                text: (link.innerText || link.textContent || '').trim(),
                            });
                        }
                    });
                } catch {}
            });

            // ===== JOB POSTINGS =====
            const jobKeywords = [
                'career', 'job', 'position', 'opening', 'hiring', 'recruitment',
                'join our team', 'we are hiring', 'work with us', 'open positions',
                'vacancy', 'employment', 'opportunity', 'role', 'apply now'
            ];

            // Check for job/career links
            document.querySelectorAll('a[href]').forEach(link => {
                const linkText = (link.innerText || link.textContent || '').toLowerCase();
                const href = link.getAttribute('href') || '';
                const hrefLower = href.toLowerCase();

                if (jobKeywords.some(keyword => 
                    linkText.includes(keyword) || hrefLower.includes(keyword)
                )) {
                    try {
                        const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                        data.jobPostings.push({
                            url: fullUrl,
                            text: (link.innerText || link.textContent || '').trim(),
                            context: link.closest('section, div, article')?.innerText?.substring(0, 200) || '',
                        });
                    } catch {}
                }
            });

            // Check for job listings on current page
            const pageText = document.body.innerText?.toLowerCase() || '';
            if (jobKeywords.some(keyword => pageText.includes(keyword))) {
                // Look for job-related sections
                const jobSections = [];
                document.querySelectorAll('section, div[class*="job"], div[class*="career"], div[id*="job"], div[id*="career"]').forEach(section => {
                    const sectionText = (section.innerText || section.textContent || '').toLowerCase();
                    if (jobKeywords.some(keyword => sectionText.includes(keyword))) {
                        jobSections.push({
                            text: (section.innerText || section.textContent || '').trim(),
                            html: section.innerHTML.substring(0, 500),
                        });
                    }
                });
                if (jobSections.length > 0) {
                    data.jobPostings.push({
                        url: window.location.href,
                        text: 'Job listings found on page',
                        sections: jobSections,
                    });
                }
            }

            // ===== EMAIL ADDRESSES =====
            const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
            const pageContent = document.body.innerText || document.body.textContent || '';
            const emails = [...new Set(pageContent.match(emailPattern) || [])];
            
            // Filter out common non-contact emails
            const filteredEmails = emails.filter(email => {
                const lower = email.toLowerCase();
                return !lower.includes('example.com') && 
                       !lower.includes('test.com') &&
                       !lower.includes('placeholder');
            });
            
            data.addresses.email = filteredEmails;

            // ===== PHYSICAL ADDRESSES =====
            const addressPatterns = [
                /\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|way|court|ct|place|pl)[\s,]+[\w\s,]+(?:\d{5}(?:-\d{4})?)?/gi,
                /[\w\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?/gi,
                /[\w\s]+,\s*[\w\s]+,\s*[A-Z]{2}\s+\d{5}/gi,
            ];

            const addresses = new Set();
            addressPatterns.forEach(pattern => {
                const matches = pageContent.match(pattern);
                if (matches) {
                    matches.forEach(addr => {
                        const cleanAddr = addr.trim();
                        if (cleanAddr.length > 10 && cleanAddr.length < 200) {
                            addresses.add(cleanAddr);
                        }
                    });
                }
            });

            // Also check for address in structured data
            document.querySelectorAll('address, [itemprop="address"], .address, #address').forEach(addrEl => {
                const addrText = (addrEl.innerText || addrEl.textContent || '').trim();
                if (addrText.length > 10) {
                    addresses.add(addrText);
                }
            });

            data.addresses.physical = Array.from(addresses);

            // ===== COMPLIANCE INFORMATION (ISO, SOC2, GDPR) =====
            const complianceKeywords = {
                iso: ['iso 27001', 'iso9001', 'iso 9001', 'iso27001', 'iso certification', 'iso certified'],
                soc2: ['soc 2', 'soc2', 'soc type ii', 'soc type 2', 'soc ii', 'soc2 certified', 'soc 2 certified'],
                gdpr: ['gdpr', 'gdpr compliant', 'general data protection regulation', 'gdpr compliant'],
            };

            const pageTextLower = pageContent.toLowerCase();
            
            Object.keys(complianceKeywords).forEach(type => {
                complianceKeywords[type].forEach(keyword => {
                    if (pageTextLower.includes(keyword)) {
                        // Find context around the keyword
                        const index = pageTextLower.indexOf(keyword);
                        const context = pageContent.substring(
                            Math.max(0, index - 100),
                            Math.min(pageContent.length, index + keyword.length + 200)
                        );
                        
                        data.compliance[type].push({
                            keyword: keyword,
                            context: context.trim(),
                            url: window.location.href,
                        });
                    }
                });
            });

            // Check for compliance badges/logos
            document.querySelectorAll('img[alt*="iso"], img[alt*="soc"], img[alt*="gdpr"], img[src*="iso"], img[src*="soc"], img[src*="gdpr"]').forEach(img => {
                const alt = img.getAttribute('alt') || '';
                const src = img.getAttribute('src') || '';
                const complianceType = 
                    (alt.toLowerCase().includes('iso') || src.toLowerCase().includes('iso')) ? 'iso' :
                    (alt.toLowerCase().includes('soc') || src.toLowerCase().includes('soc')) ? 'soc2' :
                    (alt.toLowerCase().includes('gdpr') || src.toLowerCase().includes('gdpr')) ? 'gdpr' : 'other';
                
                data.compliance[complianceType].push({
                    type: 'badge',
                    alt: alt,
                    src: src.startsWith('http') ? src : new URL(src, baseUrlString).href,
                    url: window.location.href,
                });
            });

            // ===== TEAM MEMBERS =====
            const teamKeywords = ['team', 'about us', 'our team', 'meet the team', 'leadership', 'founders', 'executives'];
            
            // Check for team section
            const teamSections = [];
            document.querySelectorAll('section, div[class*="team"], div[id*="team"], div[class*="about"], div[id*="about"]').forEach(section => {
                const sectionText = (section.innerText || section.textContent || '').toLowerCase();
                if (teamKeywords.some(keyword => sectionText.includes(keyword))) {
                    teamSections.push(section);
                }
            });

            teamSections.forEach(section => {
                // Look for team member cards
                section.querySelectorAll('div[class*="member"], div[class*="person"], div[class*="team"], article, .card').forEach(member => {
                    const nameEl = member.querySelector('h1, h2, h3, h4, [class*="name"], [class*="title"]');
                    const roleEl = member.querySelector('[class*="role"], [class*="position"], [class*="title"]:not(h1):not(h2):not(h3):not(h4)');
                    const bioEl = member.querySelector('p, [class*="bio"], [class*="description"]');
                    const imageEl = member.querySelector('img');
                    
                    const name = nameEl ? (nameEl.innerText || nameEl.textContent || '').trim() : '';
                    const role = roleEl ? (roleEl.innerText || roleEl.textContent || '').trim() : '';
                    const bio = bioEl ? (bioEl.innerText || bioEl.textContent || '').trim() : '';
                    const image = imageEl ? (imageEl.getAttribute('src') || '') : '';

                    if (name || role) {
                        data.teamMembers.push({
                            name: name,
                            role: role,
                            bio: bio.substring(0, 300),
                            image: image.startsWith('http') ? image : new URL(image, baseUrlString).href,
                        });
                    }
                });

                // Also check for linkedin profiles in team section
                section.querySelectorAll('a[href*="linkedin.com"]').forEach(link => {
                    const href = link.getAttribute('href');
                    const parentText = link.closest('div, article, section')?.innerText || '';
                    const nameMatch = parentText.match(/^[\w\s]{2,50}/);
                    
                    if (nameMatch && !data.teamMembers.some(m => m.linkedin === href)) {
                        data.teamMembers.push({
                            name: nameMatch[0].trim(),
                            linkedin: href,
                        });
                    }
                });
            });

            // ===== PRICING INFORMATION =====
            const pricingKeywords = ['pricing', 'price', 'cost', 'plan', 'subscription', 'tier', 'pricing table', 'pricing plans'];
            
            // Check for pricing sections
            const pricingSections = [];
            document.querySelectorAll('section, div[class*="pric"], div[id*="pric"], div[class*="plan"], div[id*="plan"]').forEach(section => {
                const sectionText = (section.innerText || section.textContent || '').toLowerCase();
                if (pricingKeywords.some(keyword => sectionText.includes(keyword))) {
                    pricingSections.push(section);
                }
            });

            pricingSections.forEach(section => {
                // Look for price values
                const pricePattern = /\$[\d,]+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP|\$|€|£)|free|contact us|request quote/gi;
                const sectionText = section.innerText || section.textContent || '';
                const prices = sectionText.match(pricePattern) || [];

                if (prices.length > 0) {
                    // Extract plan names
                    const planNames = [];
                    section.querySelectorAll('h1, h2, h3, h4, [class*="plan"], [class*="tier"]').forEach(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text && text.length < 50) {
                            planNames.push(text);
                        }
                    });

                    pricingSections.push({
                        text: sectionText.substring(0, 1000),
                        prices: prices,
                        planNames: planNames,
                        url: window.location.href,
                    });
                }
            });

            // Also check pricing table
            document.querySelectorAll('table[class*="pric"], table[id*="pric"]').forEach(table => {
                const rows = [];
                table.querySelectorAll('tr').forEach(row => {
                    const cells = Array.from(row.querySelectorAll('td, th')).map(cell => 
                        (cell.innerText || cell.textContent || '').trim()
                    );
                    if (cells.length > 0) {
                        rows.push(cells);
                    }
                });
                
                if (rows.length > 0) {
                    data.pricing.push({
                        type: 'table',
                        data: rows,
                        url: window.location.href,
                    });
                }
            });

            data.pricing = pricingSections;

            return data;
        }, targetUrl);

        // ===== FOLLOW IMPORTANT LINKS =====
        const additionalPages = [];
        if (CONFIG.followLinks) {
            console.log('\n🔗 Discovering important links (Careers, Pricing, About, etc.)...');
            const importantLinks = await discoverImportantLinks(page, baseUrl);
            
            if (importantLinks.length > 0) {
                console.log(`Found ${importantLinks.length} important links to follow:`);
                importantLinks.forEach(link => {
                    console.log(`  - ${link.type}: ${link.text} (${link.url})`);
                });
                
                for (let i = 0; i < importantLinks.length; i++) {
                    const link = importantLinks[i];
                    const pageData = await scrapeAdditionalPage(page, link.url, browser, link.type);
                    if (pageData) {
                        additionalPages.push(pageData);
                    }
                    
                    // Add delay between pages
                    if (i < importantLinks.length - 1) {
                        await randomDelay(1500, 2500);
                    }
                }
                console.log(`\n✅ Scraped ${additionalPages.length} additional pages\n`);
            }
        }

        // ===== DISCOVER AND SCRAPE BLOG POSTS =====
        console.log('\n📰 Discovering blog posts and news articles...');
        
        // First, find blog listing pages and follow pagination
        const blogListingPages = [targetUrl]; // Start with main page
        const visitedBlogPages = new Set([targetUrl]);
        
        if (CONFIG.followBlogPagination) {
            console.log('🔍 Looking for blog pagination...');
            
            // Check current page for pagination
            let currentPage = targetUrl;
            let pagesToCheck = 1;
            
            while (pagesToCheck <= CONFIG.maxBlogPages && currentPage) {
                await page.goto(currentPage, { 
                    waitUntil: CONFIG.waitFor, 
                    timeout: CONFIG.timeout 
                });
                await randomDelay(1000, 2000);
                
                const paginationLinks = await findBlogPaginationLinks(page, baseUrl);
                
                if (paginationLinks.length > 0) {
                    const nextPage = paginationLinks[0].url;
                    if (!visitedBlogPages.has(nextPage)) {
                        console.log(`  📄 Found blog pagination: ${nextPage}`);
                        blogListingPages.push(nextPage);
                        visitedBlogPages.add(nextPage);
                        currentPage = nextPage;
                        pagesToCheck++;
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            }
            
            console.log(`Found ${blogListingPages.length} blog listing pages to scrape\n`);
        }
        
        // Collect blog posts from all listing pages
        const blogPosts = [];
        const allBlogPostUrls = new Map(); // Use Map to store url -> post info
        
        for (const listingPage of blogListingPages) {
            await page.goto(listingPage, { 
                waitUntil: CONFIG.waitFor, 
                timeout: CONFIG.timeout 
            });
            await randomDelay(1000, 2000);
            
            const blogPostUrls = await page.evaluate((baseUrlString) => {
            const urls = [];
            const seenUrls = new Set();
            
            // Helper function to check if URL is a blog post
            function checkIsBlogPost(url, pathname) {
                const blogIndicators = [
                    '/blog/', '/posts/', '/article/', '/news/', '/press/', 
                    '/journal/', '/updates/', '/archive/', '/category/', 
                    '/tag/', '/author/', '/date/', '/2024/', '/2023/', '/2022/',
                    '/story/', '/post/', '/read/', '/content/'
                ];
                
                const lowerUrl = url.toLowerCase();
                const lowerPath = pathname.toLowerCase();
                
                return blogIndicators.some(indicator => 
                    lowerUrl.includes(indicator) || lowerPath.includes(indicator)
                );
            }
            
            // Find blog post links
            const blogKeywords = ['blog', 'post', 'article', 'news', 'press', 'journal', 'story'];
            
            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                if (!href) return;
                
                try {
                    const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                    const urlObj = new URL(fullUrl);
                    const pathname = urlObj.pathname.toLowerCase();
                    const urlLower = fullUrl.toLowerCase();
                    
                    // Check if it's a blog post URL
                    const isBlog = checkIsBlogPost(fullUrl, pathname) || 
                                   blogKeywords.some(keyword => pathname.includes(keyword) || urlLower.includes(keyword));
                    
                    // Check if link text suggests it's a post
                    const linkText = (link.innerText || link.textContent || '').toLowerCase();
                    const isPostLink = blogKeywords.some(keyword => linkText.includes(keyword));
                    
                    if (isBlog || isPostLink) {
                        if (!seenUrls.has(fullUrl) && urlObj.hostname === new URL(baseUrlString).hostname) {
                            const title = (link.innerText || link.textContent || '').trim();
                            urls.push({
                                url: fullUrl,
                                title: title || '',
                                context: link.closest('article, section, div')?.innerText?.substring(0, 200) || '',
                            });
                            seenUrls.add(fullUrl);
                        }
                    }
                } catch {}
            });
            
            // Also check for blog listing pages
            const blogListingSelectors = [
                '[class*="blog"]',
                '[id*="blog"]',
                '[class*="post"]',
                '[class*="article"]',
                '[class*="news"]',
            ];
            
            blogListingSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(container => {
                    container.querySelectorAll('a[href]').forEach(link => {
                        const href = link.getAttribute('href');
                        if (!href) return;
                        
                        try {
                            const fullUrl = href.startsWith('http') ? href : new URL(href, baseUrlString).href;
                            const urlObj = new URL(fullUrl);
                            
                            if (!seenUrls.has(fullUrl) && urlObj.hostname === new URL(baseUrlString).hostname) {
                                const title = (link.innerText || link.textContent || '').trim();
                                if (title && title.length > 10) {
                                    urls.push({
                                        url: fullUrl,
                                        title: title,
                                        context: '',
                                    });
                                    seenUrls.add(fullUrl);
                                }
                            }
                        } catch {}
                    });
                });
            });
            
            return urls;
            }, listingPage);
            
            // Add URLs from this page to the collection
            blogPostUrls.forEach(post => {
                if (!allBlogPostUrls.has(post.url)) {
                    allBlogPostUrls.set(post.url, post);
                }
            });
        }
        
        // Convert to array and limit
        const blogPostUrlsArray = Array.from(allBlogPostUrls.values()).slice(0, CONFIG.maxBlogPosts);
        
        console.log(`Found ${blogPostUrlsArray.length} potential blog posts/articles across ${blogListingPages.length} pages`);

        // Scrape each blog post
        for (let i = 0; i < blogPostUrlsArray.length; i++) {
            const postInfo = blogPostUrlsArray[i];
            console.log(`\n[${i + 1}/${blogPostUrlsArray.length}] Scraping: ${postInfo.title || postInfo.url}`);
            
            const postData = await scrapeBlogPost(page, postInfo.url, browser);
            
            if (postData && postData.content && postData.content.length > 100) {
                blogPosts.push(postData);
            }
            
            // Add delay between posts
            if (i < blogPostUrlsArray.length - 1) {
                await randomDelay(1000, 2000);
            }
        }

        console.log(`\n✅ Scraped ${blogPosts.length} blog posts/articles`);

        console.log('📝 Summarizing texts...');
        
        // Summarize text sections using AI
        for (let i = 0; i < scrapedData.texts.sections.length; i++) {
            const section = scrapedData.texts.sections[i];
            if (section.text && section.text.length > 100) {
                section.summary = await summarizeWithModel(section.text);
            }
        }

        // Add metadata
        const outputData = {
            timestamp: new Date().toISOString(),
            url: targetUrl,
            domain: baseUrl.hostname,
            ...scrapedData,
            blogPosts: blogPosts,
            additionalPages: additionalPages,
        };
        
        // Process all data through AI processor
        console.log('\n🤖 Starting AI analysis of scraped data...');
        const processedData = await processDataWithAI(outputData);

        // Display summary
        console.log('\n📊 Extraction Summary:');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log(`📄 Text Sections: ${scrapedData.texts.sections.length}`);
        console.log(`🎯 Top Banners Found: ${scrapedData.banners.length}`);
        if (scrapedData.banners.length > 0) {
            scrapedData.banners.forEach((banner, idx) => {
                const heading = banner.headings.length > 0 ? banner.headings[0].text.substring(0, 50) : 'No heading';
                console.log(`   ${idx + 1}. ${banner.className || banner.id || 'banner'} - "${heading}..."`);
            });
        }
        console.log(`📰 Blog Posts/Articles: ${blogPosts.length}`);
        console.log(`🔗 Additional Pages Scraped: ${additionalPages.length}`);
        if (additionalPages.length > 0) {
            additionalPages.forEach(page => {
                console.log(`   - ${page.pageType}: ${page.title || page.url}`);
            });
        }
        console.log(`📱 Social Media Platforms: ${Object.keys(scrapedData.socialMedia).filter(k => scrapedData.socialMedia[k].length > 0).length}`);
        console.log(`💼 Job Postings: ${scrapedData.jobPostings.length}`);
        console.log(`📧 Email Addresses: ${scrapedData.addresses.email.length}`);
        console.log(`📍 Physical Addresses: ${scrapedData.addresses.physical.length}`);
        console.log(`✅ Compliance Mentions: ISO(${scrapedData.compliance.iso.length}) SOC2(${scrapedData.compliance.soc2.length}) GDPR(${scrapedData.compliance.gdpr.length})`);
        console.log(`👥 Team Members: ${scrapedData.teamMembers.length}`);
        console.log(`💰 Pricing Information: ${scrapedData.pricing.length} sections`);
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
        
        // Display AI analysis summary if available
        if (processedData.aiAnalysis && processedData.aiAnalysis.overallSummary) {
            console.log('🤖 AI Analysis Summary:');
            console.log(`   ${processedData.aiAnalysis.overallSummary}\n`);
        }

        // Save main results to file (with AI analysis)
        const outputPath = path.join(__dirname, CONFIG.outputFile);
        fs.writeFileSync(outputPath, JSON.stringify(processedData, null, 2), 'utf8');
        console.log(`💾 Main results with AI analysis saved to: ${outputPath}`);
        
        // Save AI analysis separately
        const aiAnalysisPath = path.join(__dirname, CONFIG.aiAnalysisFile);
        const aiAnalysisData = {
            timestamp: processedData.aiAnalysis.timestamp,
            url: processedData.url,
            domain: processedData.domain,
            overallSummary: processedData.aiAnalysis.overallSummary,
            summaries: processedData.aiAnalysis.summaries,
            analyses: processedData.aiAnalysis.analyses,
        };
        fs.writeFileSync(aiAnalysisPath, JSON.stringify(aiAnalysisData, null, 2), 'utf8');
        console.log(`🤖 AI analysis saved to: ${aiAnalysisPath}`);

        // Save blog posts separately with summaries
        if (blogPosts.length > 0) {
            const blogOutputPath = path.join(__dirname, CONFIG.blogOutputFile);
            const blogOutput = {
                timestamp: new Date().toISOString(),
                sourceUrl: targetUrl,
                domain: baseUrl.hostname,
                totalPosts: blogPosts.length,
                posts: blogPosts.map(post => ({
                    url: post.url,
                    title: post.title,
                    author: post.author,
                    date: post.date,
                    summary: post.summary,
                    excerpt: post.excerpt,
                    tags: post.tags,
                    categories: post.categories,
                    wordCount: post.wordCount,
                    scrapedAt: post.scrapedAt,
                })),
            };
            fs.writeFileSync(blogOutputPath, JSON.stringify(blogOutput, null, 2), 'utf8');
            console.log(`📰 Blog posts with summaries saved to: ${blogOutputPath}\n`);
        }

        return processedData;

    } catch (error) {
        console.error('\n❌ Error scraping website:', error.message);
        throw error;
    } finally {
        await browser.close();
    }
}

// Main execution
const targetUrl = process.argv[2];

if (!targetUrl) {
    console.error('\n❌ Usage: node search_engine.js <URL>\n');
    console.error('Example: node search_engine.js https://example.com\n');
    process.exit(1);
}

scrapeWebsite(targetUrl)
    .then(() => {
        console.log('✨ Scraping completed successfully!\n');
        process.exit(0);
    })
    .catch((error) => {
        console.error('\n💥 Scraping failed:', error.message);
        process.exit(1);
    });
