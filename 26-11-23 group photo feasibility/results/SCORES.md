# Group photo scores (4 of 15 photos fully judged)

| Setup | Photos | Items listed | Right | Close | Wrong | Duplicate | Precision (right+close) | Strict precision | Recall | Strict recall | Hallucination rate | Cost / photo | Avg time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Luna 1024 px | 4 | 46 | 23 | 17 | 6 | 0 | 87% | 50% | 66% | 38% | 13% | $0.0010 | 21s |
| Luna 2048 px | 4 | 58 | 32 | 19 | 7 | 0 | 88% | 55% | 84% | 52% | 12% | $0.0013 | 45s |
| Sol 2048 px | 4 | 56 | 44 | 12 | 0 | 0 | 100% | 79% | 92% | 72% | 0% | $0.0269 | 39s |
| Luna 2x2 tiles | 4 | 63 | 31 | 23 | 9 | 0 | 86% | 49% | 89% | 51% | 14% | $0.0052 | 145s |
| Sol 2x2 tiles | 4 | 57 | 46 | 10 | 1 | 0 | 98% | 81% | 92% | 75% | 2% | $0.0916 | 149s |

- **Right**: the item and the details I care about are correct. **Close**: right item, but a detail is wrong or missing.
- **Recall** = (right + close) / number of entries a perfect list would have (my count per photo).
- **Duplicate** items are real but listed twice; they count against precision, not as hallucinations.

## What was missed (my notes)

- **IMG_1978**: it miseed the yugioh early days switch game next tot he final fantasy one. It didnt get the name right for the FF game, wiht is the pixel remaster of games 1-6. It said Trigun Maximum Vol 1-2 but its really 1 and 3. It missed the new bottle of colgne thats on the JJK hoddie. And it misclassified the popcorn container set as paper cups. also the pillow cushin is a navy blue and white BYU Y pillow.
- **IMG_6527**: technically therea belt on top of the avatr monolpoty but i dont really expect that anythig would recognmize that. Also the thing on the right of the photo is a holister winter sweater
- **IMG_6607**: I like how b was pretty good at noticing which ones were steelbooks, namely all the Ghibli films, the spiderman colelction, the yugioh bonds beyond time, the pokemin diamon and pearl 4 movie collection, wayne's world and bumbleblee. It struggled ot know where ones were sealed still and which were not. all of the ghibli's were sleaed still except for howling moving castle, castle in the sky and princess mononoke. Also, some of them struggled ot name all the ppsiderman movies (veno, spiderman into the spiderverse, homecoming and far fro home). Also some struggled to get the pokemon movies, at least saying that on of the colelctions is from black and white and one is from diamon and pearl
- **IMG_6608**: its the gaMECUBVE GAme star fox assult. And the avar adn koraa compleyte bluary sets are actually part of the same combined sety, but im not sure if that distinguishable from this angle. Also is it possible for this to figure what movies are inlcuded in that poemon 4 movie sest?
