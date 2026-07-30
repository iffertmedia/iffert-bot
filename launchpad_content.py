# -*- coding: utf-8 -*-
"""
Seed content for the Launchpad day-by-day curriculum, sourced from
"Launchpad Week Text Copy" (Iffert Media Google Doc). Cleaned of Google
Docs export artifacts (backslash-escaped punctuation, smart-chip channel
placeholders) but not summarized -- the actual training content is kept
in full.

Days 9-12 and 14 are intentionally thin in the source doc -- Week 2 is
described as being about building the daily posting habit rather than new
lessons, so there isn't more content to pull in for those days. Expand them
with /launchpad_day_edit whenever there's more to add.

This only seeds a day if it doesn't already exist in the database, so
re-deploying never overwrites edits made after the initial seed.
"""

SEED_DAYS = {
    1: {
        "title": "Welcome to TikTok GO",
        "overview": "Introduce yourself and complete your goal-setting form to kick off Launchpad.",
        "content": (
            "**Mission 1:** Introduce yourself in #launchpad-green-crew. Tell us your name, "
            "what state or city you spend the most time in, and your favorite thing to do on vacation!\n\n"
            "**Mission 2:** Complete this goal setting form: https://forms.gle/RFm2AYDWCfTXX7L37\n\n"
            "These missions must be complete before Day 2. Once you complete the missions, you can "
            "freely look at Day 2. It's in your best interest to only work on 1 day at a time, without "
            "being more than 1 day ahead. We all need to go through each day together \U0001F680\U0001F680\n\n"
            "**Topic #4: Successful videos that made sales**\n"
            "These are some of our top selling videos! Study them and see what you think is making them sell!\n"
            "https://www.tiktok.com/@luckybamboo293/video/7653968282076204302\n"
            "https://www.tiktok.com/@travelwithlatanyac/video/7635888801944030494\n"
            "https://www.tiktok.com/@travelwithlatanyac/video/7649024138811641118\n"
            "https://www.tiktok.com/@nashintune/video/7638273223750077727\n"
            "https://www.tiktok.com/@avy.cest.moi/video/7645016921385028895\n"
            "https://www.tiktok.com/@avy.cest.moi/video/7616834359143746846\n"
            "https://www.tiktok.com/@wanderstacked/video/7649189901744819487\n\n"
            "**Topic #6: What Launchpad unlocks**\n"
            "What does Launchpad unlock?\n"
            "- Iffert Media rewards (cash, equipment and more!)\n"
            "- Events (hotel visits, hotel hops, group dining)\n"
            "- Posting challenges for additional rewards\n"
            "- Opportunities for hosting creator events, applying for City Lead, free hotel stays, etc\n"
            "- Creator Level channels to grow with your community\n"
            "If you have been to our events before or plan on going to events during this Launchpad, "
            "you are more than welcome to attend! You will not get rewards from the event until you "
            "complete Launchpad."
        ),
    },
    2: {
        "title": "Learn Iffert Media Discord",
        "overview": "Explore the Iffert Media Discord -- check out #library, react in #newsroom, and read the Content Policy.",
        "content": (
            "**Mission 1:** Go to #library and read everything you can to learn more about Iffert Media "
            "and TikTok GO.\n"
            "**Mission 2:** React to a recent message in #newsroom.\n"
            "**Mission 3:** Read 'Content Policy'! Go to TikTok Studio > TikTok GO > Tap the 'All toolkits' "
            "button in the middle section of the screen > Select 'Content policy'.\n"
            "**Bonus Mission:** Go to TikTok Studio > TikTok GO > Tap 'Growth' at the bottom > "
            "'Your growth guide' arrow > Tap 'All courses' at the top > Watch the 7 videos.\n\n"
            "These missions must be complete before Day 3. Once you complete the missions, you can "
            "freely look at Day 3. It's in your best interest to only work on 1 day at a time, without "
            "being more than 1 day ahead. We all need to go through each day together \U0001F680\U0001F680\n\n"
            "**Topic #1: Overview of channels**\n"
            "Once you complete Launchpad, you'll have access to more channels in our Discord server! "
            "Here's a breakdown:\n"
            "GO Creators - anyone in our agency before leveling up to L1\n"
            "L1 - you've made a sale(s) up to $4,000 last month/this month\n"
            "L2 - you've made between $4,000-$30,000 last month/this month\n"
            "L3 - you've made over $30,000 last month/this month\n\n"
            "Important channels to check daily: #newsroom, #chatroom, #library, #side-quests\n\n"
            "City channel list -- you only have access to your home city: Nashville, Orlando, Atlanta, "
            "Gatlinburg/Knoxville/Pigeon Forge/East TN, SoCal, New Orleans, Chicago, Tampa, "
            "Destin/Pensacola/Gulf Shores/Panama City, Alabama, Hawaii, North Carolina, South Carolina\n\n"
            "**Topic #2: What roles mean and how to get access to roles**\n"
            "GO Director (Iffert Media Staff): Do not DM unless instructed.\n"
            "GO Leader (City Leads): You get this role if you apply and get selected as a city lead in "
            "cities that need one.\n"
            "Creator Level roles:\n"
            "GO Creator (L0): you have not made a sale, or you've been dropped from L1\n"
            "L1: you get this role as soon as you make a sale\n"
            "L2: you get this role as soon as you make over $4K in sales within 1 calendar month\n"
            "L3: you get this role as soon as you make over $30K in sales within 1 calendar month\n"
            "L4: you get this role as soon as you make over $140K in sales within 1 calendar month\n"
            "You drop a level if you don't meet the threshold for a certain level within 1 calendar month. "
            "Example: if you are L2 this month but don't get over $4K sales this month, you are dropped "
            "to L1 or L0.\n\n"
            "**Topic #4: How to add all channels to your Discord**\n"
            "Scroll to the top of your channel list, click 'Channels and Roles', select 'Browse Channels' "
            "at the top, and add all the channels you want. For #newsroom, you may need to go to "
            "'Server Guide' first and click through from there.\n\n"
            "**Topic #5: Set yourself up for success**\n"
            "1. Make sure you have storage on your phone to record footage.\n"
            "2. Ensure your camera settings are sufficient for quality videos (4K at 60fps).\n"
            "3. Don't plan on recording during low lighting, dark settings.\n"
            "4. Keep your battery charged with no low power mode -- camera quality drops in low power mode.\n"
            "5. Charge an external power bank for emergencies.\n"
            "6. If you can't film your own content during this Launchpad, check the Hotel Content Bank "
            "and learn how to use those clips for a TikTok GO video.\n"
            "7. Browse Google Maps to find hotels near you, then search for them in TikTok GO Marketplace "
            "to plan your commute for this weekend.\n"
            "8. Review Day 1.\n"
            "9. Ask questions in #launchpad-green-crew."
        ),
    },
    3: {
        "title": "Filming Standards",
        "overview": "Time to film! Shoot your first hotel video and submit it for feedback (don't post it yet).",
        "content": (
            "**Mission 1:**\n"
            "1. Check the Hotel Content Bank.\n"
            "2. Select a hotel you want to post (use your own footage from your phone if you want).\n"
            "3. Edit in TikTok or CapCut however you want (just music, music and text on screen, "
            "voiceover, etc). Use your creative freedom!\n"
            "4. Do not post the video. Download it and send it in this thread for feedback. You'll post "
            "the revised version on Day 4.\n\n"
            "This mission must be complete before Day 4. It's in your best interest to only work on 1 day "
            "at a time, without being more than 1 day ahead. We all need to go through each day together \U0001F680\U0001F680\n\n"
            "**Topic #1: Camera Movement**\n"
            "Don't move too fast when recording -- going too fast makes your video blurry. Be diverse "
            "with your camera movement (not just left-to-right -- try bottom-to-top or top-to-bottom too), "
            "and keep it slow and steady. Film the same thing from multiple angles and with different "
            "movements -- always record more footage than you think you need. Start at .5x, then switch to "
            "1x for close-ups. Never film at a downward angle -- keep your phone chest level, never above "
            "your head, or you'll get too much ground in the shot.\n\n"
            "**Topic #2: Shot Selection**\n"
            "Pick the shots with the best lighting and appropriate speed for the video. The best videos "
            "use the highest quality clips on purpose, with natural movement. Keep an eye on the flow of "
            "shots so the full video feels well thought out. Have someone record clips of you if possible.\n\n"
            "**Topic #3: Pacing**\n"
            "Luxury hotels/resorts: slower pace, longer shots, longer video. Budget hotels: faster pace, "
            "shorter shots, 16 seconds minimum. Make sure your sound matches the content you shot -- "
            "cozier beats for warmer shots, upbeat songs for modern locations. If you have an older phone, "
            "shoot slowly and intentionally (you can always speed footage up later, but slowing footage "
            "down tanks quality). Voiceovers should be at a digestible pace with good dictation. Walk at "
            "a slower pace with the camera at chest level for moving shots.\n\n"
            "**Topic #5: Call To Action (CTA)**\n"
            "The one thing you want people to do in your video: click the location tag. Use text on "
            "screen, voiceover, a sticker, or point on camera -- always show where to book. 90% of TikTok "
            "users still don't know they can book travel directly from TikTok.\n"
            "Where to put a CTA: right after the hook, towards the end, or at the very end (test it). "
            "For major campaigns, put the CTA at the beginning with the discount mentioned.\n"
            "CTA types: text overlay, voiceover ('tap Sound then Voiceover'), sticker (arrow, 'book now', "
            "circle), pointing on camera, or green-screening yourself pointing at the location tag.\n"
            "Why it matters: it drives your CTR. If you skip a CTA on a video that's fine (that's called "
            "an evergreen video) but skipping it everywhere hurts your chances of making commission.\n\n"
            "**Topic #6: Click Through Rate (CTR)**\n"
            "CTR = how many people click the location tag / views. This is the best metric to look at "
            "first for commission -- high views and viral videos don't always mean sales. Top creators get "
            "sales from any amount of views.\n"
            "How to raise CTR: tell the viewer where/how/why to click, mention the sale price, show an "
            "image sticker of exactly what to book, add a sticker showing where to book, and start with "
            "a strong hook.\n"
            "How to check it: TikTok Studio > TikTok GO > All toolkits > Analytics > Content > pick a "
            "video > scroll to 'Location tag click rate'. Average CTR for hotels: .75%. Average CTR for "
            "TTD: .66%. Below average means your video isn't enticing enough -- try a different CTA or "
            "move it elsewhere in the video.\n\n"
            "**Topic #7: What Makes a High Quality Video**\n"
            "Clearly shows everything in the space, high resolution (aim for 4K/60fps), phone charged and "
            "off low power mode, moving slower if you don't have a newer phone camera. Turn on 'allow "
            "high quality uploads' when posting. Every video needs a CTA and a hook. Film in good "
            "lighting. Mention the sale price. Speak clearly in voiceovers. Keep the camera steady -- walk "
            "slower if needed, and turn on 'Enhanced Stabilization' in your camera settings.\n"
            "Post in this channel for feedback!"
        ),
    },
    4: {
        "title": "Creator Growth Opportunities",
        "overview": "Post your revised video through a Tasks with Rewards leaderboard and share your screenshot.",
        "content": (
            "**Mission 1:**\n"
            "1. Go to TikTok Studio > TikTok GO > All toolkits > Tasks with rewards.\n"
            "2. Find the crown icon and tap 'Join' or 'Post' -- that's your leaderboard for the rest of "
            "Launchpad.\n"
            "3. Inside the Leaderboard page, find the required hashtag for your video description and "
            "copy it.\n"
            "4. Go to 'Tasks with rewards', find the star icon, and choose one task to focus on. Read the "
            "requirements.\n"
            "5. Tap 'Choose outlet to post', search for your hotel, tap it, then tap 'Post'.\n"
            "6. Upload your Day 3 video, write your description, and make sure the correct location is "
            "chosen before publishing.\n"
            "7. Publish, then send a screenshot of the task page (showing your video) in this thread to "
            "complete the mission. We'll help if you don't see it show up.\n\n"
            "These missions must be complete before Day 5. Do not look at Day 2, Day 7, or Week 2 yet! "
            "We all need to go through each day together \U0001F680\U0001F680\n\n"
            "**Topic #1: How Iffert Media Rewards Work**\n"
            "You earn rewards by completing challenges, found in #side-quests and announced in "
            "#newsroom (also check your level channel -- some challenges are level-specific).\n"
            "Submission varies by challenge: hotel challenges get submitted in the designated thread; "
            "large posting challenges (e.g. a 50-video challenge) are tracked in a spreadsheet you submit "
            "to the designated team member; monthly/weekly challenges go through a Google form or "
            "collaboration package.\n"
            "Read every challenge's requirements carefully -- hashtags and video types differ, and missing "
            "them means no reward. Submissions are due by 11:59pm the day before the deadline; late "
            "submissions aren't accepted. Every TikTok GO video must be 16+ seconds. Rewards for a given "
            "month are paid out mid the following month via PayPal or Venmo.\n\n"
            "**Topic #2: How Collaborations Work**\n"
            "Collaborations come from travel brands, Iffert Media, or TikTok GO. Tabs: To apply, In "
            "progress, Completed, Canceled. We use collabs for easy submission access to specific "
            "challenges and rewards -- some are open to everyone, some to specific groups. You'll get a "
            "system notification when added to one. Find yours at TikTok Studio > TikTok GO > All "
            "toolkits > Collaborations. No collabs yet? That's fine -- focus on tasks and leaderboards. "
            "Missing an expected Iffert Media collab? Flag it in #side-quests (we don't answer DMs about "
            "it). Side quests become visible after Launchpad.\n\n"
            "**Topic #3: How Iffert Media Events Work**\n"
            "Three event types:\n"
            "**Hotel Hops** -- open to every creator, a guided shoot at 5 hotels in 2-4 hours. No room "
            "tours/amenities/free food unless noted. You don't need room footage to make sales. Sign up "
            "via the Discord event calendar and click Interested (unclick if you can't make it -- no "
            "shows affect future invites). You'll be added to an event thread at least 1 day ahead. Show "
            "up to the first location, wait for the group, and your Agency POC will run the day -- usually "
            "5-15 minutes per hotel, lobby recorded last (so you keep footage even if asked to leave "
            "early). Don't talk to staff -- let your POC handle it. Don't ask to see a room, don't be loud, "
            "record more than you think you need.\n"
            "**Scheduled Hotel Visits** -- planned in advance with the hotel, so you'll get a room tour, "
            "amenity tour, and sometimes food (details in the event post). Same sign-up process. Don't be "
            "late -- you'll miss the tour. During the visit: don't run water/appliances/move furniture, "
            "keep noise down (paying guests are present), record more than you think you need.\n"
            "**Special Hotel Events** (e.g. a launch event) -- Iffert Media pays for space/F&B to get "
            "tours; guaranteed Iffert Media presence. Same sign-up process. Expect a room/amenity tour, "
            "a TikTok GO presentation, food & drinks, and a giveaway. Food/drinks aren't always "
            "complimentary -- check event details first. You must post at least 2 videos about the hotel "
            "afterward to receive rewards, submitted on the schedule given in the event thread.\n\n"
            "**Topic #4: POI Selection**\n"
            "Use TikTok GO Studio's Marketplace filter (hotels or things to do) to see which places have "
            "the most sales -- a high performer is a good target, or try a low performer for A/B testing "
            "potential. Look for real selling points: pool, gym, guest laundry, restaurant/bar, "
            "complimentary breakfast, location. Level-specific POI lists are linked in your level "
            "channels once you complete Launchpad.\n\n"
            "**Topic #5: Analytics**\n"
            "Post at least once a day to get meaningful analytics. Find yours at TikTok Studio > TikTok "
            "GO > All toolkits > Analytics -- three tabs: Transactions (sales value, commission, products "
            "sold/redeemed), Content (per-video CTR, CVR, sales -- the most important metrics; don't chase "
            "views), and Traffic (overall posting/engagement metrics). Low CTR means your CTA isn't "
            "landing; high CTR but low CVR means try another video with a clearer price/option sticker. "
            "Posting consistently for a month with no sales? Book a coaching call with Sunny or Laura. "
            "Some creators take 1 week to 2 months to get a first sale -- stay consistent and keep "
            "improving, don't quit.\n\n"
            "**Topic #6: Hashtags and Keywords**\n"
            "Use required hashtags for specific events/challenges (e.g. #iffertmediago). Pull specific "
            "keywords from your location (e.g. #orlandoresort, #Hiltondowntownnashville). Use at least 3 "
            "hashtags (up to 5), and be specific. Never use #tiktokgo, #viral, #fyp, or other "
            "viral-chasing tags. Keywords matter because TikTok is search-based -- use them in text "
            "overlay, description, spoken narration, and hashtags.\n\n"
            "**Topic #7: Consistency and Variety**\n"
            "Post at least one TikTok GO video daily to train your algorithm and build sales -- that's "
            "exactly the habit this Launchpad builds. Aim for at least 5 videos per hotel visit by "
            "capturing varied clips (gym, lobby, pool individually, then combined). If using the content "
            "bank, the same approach works -- 5 different videos from one set of clips."
        ),
    },
    5: {
        "title": "Collaborations",
        "overview": "Review the Hotel Framework and TTD video tips, then complete your Collaboration Readiness Checklist.",
        "content": (
            "**Topic #1:** Brief overview of how to post and earn money with TikTok GO.\n\n"
            "**Topic #2: Video Ideas for Hotels (ACC)**\n"
            "Successful creators record more than they think they need. Don't just post 1 video per "
            "hotel -- post multiple so you can refine what actually sells (amenities, room, location, "
            "you, restaurant, etc).\n"
            "Try: voiceover with music, voiceover with no music, voiceover with text overlay, just music "
            "with text overlay, green-screen floating head over your hotel footage.\n"
            "Film: exterior, lobby, restaurant/bar/dining, artwork, proximity to nearby venues, POV with "
            "you on camera, room (multiple angles, multiple videos), unique features, rooftop if there "
            "is one.\n\n"
            "**Topic #3: Hotel Framework**\n"
            "You are a Hotel Advisor, not an influencer -- influencers chase views, you chase sales. "
            "Saying every hotel is amazing isn't sustainable and reads as inauthentic. Following a "
            "script (ChatGPT, the Hotel Framework, etc) means you're telling viewers why to book "
            "before they go check Google or someone else's video. You don't have to follow the Hotel "
            "Framework during Launchpad, but refer back to it when making videos -- ask yourself 'why "
            "would I book here' and 'would this make me want to book right now.' Include honesty: "
            "\"You're trading an ultra luxury stay for a bigger room and more amenities\" or \"The room "
            "isn't fully renovated, but you're here for X, where you wouldn't spend much time in the "
            "room anyway.\"\n\n"
            "**Topic #4: How to Post a Successful TTD Video**\n"
            "Grab attention in the first 3 seconds with your best clip. Show the location right after so "
            "viewers know what they're seeing. Highlight the best attractions/features, share your "
            "genuine experience and why it's worth visiting, use clear voiceover or text, consider a "
            "green screen showing how to book, keep it moving with multiple clips, and end with a clear "
            "CTA. Follow TikTok GO's task/leaderboard requirements and policies. The best TTD videos "
            "feel authentic and help viewers imagine themselves there.\n\n"
            "**Topic #5: How Collaborations Work (review)**\n"
            "Collaborations come from travel brands, Iffert Media, or TikTok GO. Tabs: To apply, In "
            "progress, Completed, Canceled. You'll need to keep posting in your collaborations for the "
            "rest of Launchpad. Find yours at TikTok Studio > TikTok GO > All toolkits > Collaborations. "
            "No collabs showing? Let us know in #launchpad-green-crew ASAP.\n\n"
            "**Mission:** Complete the Collaboration Readiness Checklist."
        ),
    },
    6: {
        "title": "Go Out and Record Hotel Footage",
        "overview": "Optional but recommended: go out and record hotel footage to get ahead for Week 2.",
        "content": (
            "No missions are required today. This is only going to help you next week!\n\n"
            "This mission is not mandatory, but it'll help you post in Week 2 -- you'll be posting 1 ACC "
            "video and 1 TTD video each day. Let us know in #launchpad-green-crew which hotel you visited!"
        ),
    },
    7: {
        "title": "Sunday Reset",
        "overview": "Sunday Reset -- take 30 minutes to review your checklist and get ready for Week 2.",
        "content": (
            "Not mandatory, but it sets you up for success in Week 2. Take 30 minutes today (in a few "
            "chunks if needed) to go over the Sunday Reset checklist. We want to see you get certified so "
            "you can access cash rewards, challenges, creator events, and other opportunities!"
        ),
    },
    8: {
        "title": "Week One Review",
        "overview": "Week One Review -- post 1 ACC video and 1 TTD video, and review what you learned in Days 1-4.",
        "content": (
            "**Topics to review:** Day 1, Day 2, Day 3, Day 4.\n\n"
            "**Mission:** Post 1 ACC video in your collaboration task, and post 1 TTD video in your "
            "collaboration task.\n\n"
            "**Get ahead for the week:** you'll post 1 ACC video and 1 TTD video Monday through Friday. "
            "Saturday and Sunday are makeup days."
        ),
    },
    9: {
        "title": "Post Video",
        "overview": "Keep the streak alive -- post 1 ACC video and 1 TTD video today.",
        "content": (
            "Keep building the habit: post 1 ACC video and 1 TTD video today. This is what Week 2 is "
            "really about -- consistency. Every video you post trains the algorithm and builds toward "
            "your first sale."
        ),
    },
    10: {
        "title": "Post Video",
        "overview": "Keep the streak alive -- post 1 ACC video and 1 TTD video today.",
        "content": (
            "Keep building the habit: post 1 ACC video and 1 TTD video today. Stay consistent -- this is "
            "the routine you'll carry with you as a creator after Launchpad."
        ),
    },
    11: {
        "title": "Post Video",
        "overview": "Keep the streak alive -- post 1 ACC video and 1 TTD video today.",
        "content": (
            "Keep building the habit: post 1 ACC video and 1 TTD video today. If you're falling behind, "
            "remember Saturday and Sunday are your makeup days."
        ),
    },
    12: {
        "title": "Post Video",
        "overview": "Keep the streak alive -- post 1 ACC video and 1 TTD video today.",
        "content": (
            "Keep building the habit: post 1 ACC video and 1 TTD video today. You're almost through the "
            "two weeks -- keep the consistency up."
        ),
    },
    13: {
        "title": "Makeup Day",
        "overview": "Makeup day -- catch up on anything you're behind on so you can get certified Monday.",
        "content": (
            "Makeup day. If you're behind on one day's missions, use today to catch up so you can get "
            "certified on Monday.\n\n"
            "If you're behind on more than one day's missions, you won't be able to use this day as a "
            "makeup day -- you'll be moved into Launchpad Holding until the next cohort starts."
        ),
    },
    14: {
        "title": "Final Day",
        "overview": "Final day -- wrap up your missions and get ready for certification.",
        "content": (
            "\u26A0\uFE0F This day's content is incomplete in the source document (it cuts off after "
            "\"Plan when you will...\"). Use /launchpad_day_edit to finish writing Day 14 once the rest "
            "of the plan is decided."
        ),
    },
}
