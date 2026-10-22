# MOE loanword appendix import, 2026-10-22

## Scope and source

The maintainer requested all 172 records from the MOE 外來詞 appendix in a separate Jujutsu workspace. The new workspace is `moe-loanwords` at `/private/tmp/hanlo-moe-loanwords-import`, based on working change `orppoulq` (snapshot `2bf55ea8`). This includes the current default workspace additions and their ID reservations so duplicate checks and subsequent allocation use the current lexicon. The original workspace is unchanged.

The authoritative import source is the existing pinned original ODS, snapshot `moe-kautian-3e0b2023e0bd`, SHA-256 `3e0b2023e0bd1448a5a620e989670bc428079c257ff8522024e2aedfa90fe071`. Select the 172 records with 分類 = 外來詞 and 詞目類型 = 附錄 from sheet 詞目, rows 24238–24409, MOE IDs 20364–20535. No source snapshot or pin is changed.

The online listing also reports 172 records: [1–100](https://sutian.moe.edu.tw/zh-hant/huliok/104/?iahbe=1&pitsoo=100) and [101–172](https://sutian.moe.edu.tw/zh-hant/huliok/104/?iahbe=2&pitsoo=100). Each new entry preserves the original appendix spelling as both preferred form and canonical TL and cites its original ODS row. Only these canonical appendix readings are imported; additional readings elsewhere in the dictionary are not inferred.

## Result

152 nonconflicting entries were added through `tools/lexicon.py add`, using its writer lock, repeated existing-entry/LKK/checksum-pinned MOE checks and ID allocation. All new entries remain `imported`. Mechanical import is not contextual model screening or individual human review. Existing entry files are unchanged.

The parser cache used by the temporary batch runner is keyed by the exact original ODS bytes; the maintenance command still checks the pinned checksum on every source load. Requests, complete offline lookup reports and add results are retained in ignored `.cache/moe-loanwords-import/` in this workspace. No maintenance tools were modified.

## Existing-entry overlaps awaiting maintainer decision

All forms below are also their approved and existing canonical readings. The 19 same-source cases propose retaining the current ID, form, readings and sources unchanged and counting the appendix word as covered, subject to explicit maintainer confirmation. Entry 689 additionally retains its existing alternate `mí-soh`.

The `pháng` case has different source identities: existing entry 729 cites 紡, MOE ID 6480, 詞目 row 6479; its definitions concern spinning yarn, turning and handling difficult matters. Appendix ID 20481 (row 24355) means bread and corresponds to substantive 麭, MOE ID 13832 (row 13826). Proposed resolution: keep entry 729 unchanged and add a separate bread word with an evidence-backed identity note and source citations. This remains pending rather than assuming that a shared spelling/reading identifies the same lexeme.

| Form / canonical TL | Existing ID | Appendix MOE ID | Appendix 詞目 row | Existing MOE identity | Proposed resolution |
| --- | ---: | ---: | ---: | --- | --- |
| bá-suh | 470 | 20375 | 24249 | Same appendix ID and row | Keep existing, count covered (pending) |
| bàng-gà | 391 | 20381 | 24255 | Same appendix ID and row | Keep existing, count covered (pending) |
| bì-lù | 428 | 20385 | 24259 | Same appendix ID and row | Keep existing, count covered (pending) |
| gá-suh | 764 | 20394 | 24268 | Same appendix ID and row | Keep existing, count covered (pending) |
| há-muh | 711 | 20400 | 24274 | Same appendix ID and row | Keep existing, count covered (pending) |
| jió-toh | 504 | 20418 | 24292 | Same appendix ID and row | Keep existing, count covered (pending) |
| kha-mé-lah | 2400 | 20421 | 24295 | Same appendix ID and row | Keep existing, count covered (pending) |
| kha-tián | 507 | 20423 | 24297 | Same appendix ID and row | Keep existing, count covered (pending) |
| kha̋n-jióo | 2403 | 20426 | 24300 | Same appendix ID and row | Keep existing, count covered (pending) |
| mí-sooh | 689 | 20465 | 24339 | Same appendix ID and row | Keep existing, count covered (pending) |
| oo-lín-gióo | 820 | 20475 | 24349 | Same appendix ID and row | Keep existing, count covered (pending) |
| oo-tóo-bái | 560 | 20477 | 24351 | Same appendix ID and row | Keep existing, count covered (pending) |
| pháng | 729 | 20481 | 24355 | 6480 紡, row 6479 | Separate bread entry (pending) |
| sa-sí-mih | 830 | 20491 | 24365 | Same appendix ID and row | Keep existing, count covered (pending) |
| se-bí-looh | 566 | 20497 | 24371 | Same appendix ID and row | Keep existing, count covered (pending) |
| siat-tooh | 833 | 20501 | 24375 | Same appendix ID and row | Keep existing, count covered (pending) |
| siat-tsuh | 569 | 20502 | 24376 | Same appendix ID and row | Keep existing, count covered (pending) |
| thài-lù | 736 | 20516 | 24390 | Same appendix ID and row | Keep existing, count covered (pending) |
| thàng-sù | 849 | 20519 | 24393 | Same appendix ID and row | Keep existing, count covered (pending) |
| ua̋i-siat-tsuh | 622 | 20534 | 24408 | Same appendix ID and row | Keep existing, count covered (pending) |

## Newly imported appendix records

| Appendix number | Form / canonical TL | MOE ID | 詞目 row | New lexicon ID |
| ---: | --- | ---: | ---: | ---: |
| 1 | a-lú-mih | 20364 | 24238 | 3073 |
| 2 | a-móo-ní-á | 20365 | 24239 | 3074 |
| 3 | a-ní-khih | 20366 | 24240 | 3075 |
| 4 | a-sír-phí-lín | 20367 | 24241 | 3076 |
| 5 | á-geh | 20368 | 24242 | 3077 |
| 6 | a̋i-sat-tsuh | 20369 | 24243 | 3078 |
| 7 | a̋i-sīr-khu-lìn-mù | 20370 | 24244 | 3079 |
| 8 | àn-nāi | 20371 | 24245 | 3080 |
| 9 | a̍t-sá-lih | 20372 | 24246 | 3081 |
| 10 | àu-tsuh | 20373 | 24247 | 3082 |
| 11 | bá-luh | 20374 | 24248 | 3083 |
| 13 | bá-tah | 20376 | 24250 | 3084 |
| 14 | bai-óo-lín | 20377 | 24251 | 3085 |
| 15 | ba̋i-khín | 20378 | 24252 | 3086 |
| 16 | bak-kuh | 20379 | 24253 | 3087 |
| 17 | bàn-bà | 20380 | 24254 | 3088 |
| 19 | ba̍t-té-lih | 20382 | 24256 | 3089 |
| 20 | bat-tah | 20383 | 24257 | 3090 |
| 21 | bi-tá-bín | 20384 | 24258 | 3091 |
| 23 | biat-tooh | 20386 | 24260 | 3092 |
| 24 | bo̍k-sìn-gù | 20387 | 24261 | 3093 |
| 25 | bòo-lù | 20388 | 24262 | 3094 |
| 26 | bòo-tòo | 20389 | 24263 | 3095 |
| 27 | bu-là-jià | 20390 | 24264 | 3096 |
| 28 | e-pú-lóng | 20391 | 24265 | 3097 |
| 29 | ga-sóo-lín | 20392 | 24266 | 3098 |
| 30 | gá-lah | 20393 | 24267 | 3099 |
| 32 | gì-tà | 20395 | 24269 | 3100 |
| 33 | giāng | 20396 | 24270 | 3101 |
| 34 | gōo-bōo | 20397 | 24271 | 3102 |
| 35 | goo-lú-huh | 20398 | 24272 | 3103 |
| 36 | ha-móo-ní-khah | 20399 | 24273 | 3104 |
| 38 | ha̋i-khé-khá-kuh | 20401 | 24275 | 3105 |
| 39 | hài-ià | 20402 | 24276 | 3106 |
| 40 | hái-kat-lá | 20403 | 24277 | 3107 |
| 41 | ha̋n-tóo-luh | 20404 | 24278 | 3108 |
| 42 | ha̋ng-góo | 20405 | 24279 | 3109 |
| 43 | hi-nóo-khih | 20406 | 24280 | 3110 |
| 44 | hoo-lú-bóng | 20407 | 24281 | 3111 |
| 45 | hoo-té-luh | 20408 | 24282 | 3112 |
| 46 | hú-looh | 20409 | 24283 | 3113 |
| 47 | iá-mih | 20410 | 24284 | 3114 |
| 48 | ia̋n-jín | 20411 | 24285 | 3115 |
| 49 | iő-káng | 20412 | 24286 | 3116 |
| 50 | ió-bih | 20413 | 24287 | 3117 |
| 51 | iú-lih | 20414 | 24288 | 3118 |
| 52 | ji-lú-bah | 20415 | 24289 | 3119 |
| 53 | jiak-kuh | 20416 | 24290 | 3120 |
| 54 | jiàn-bà | 20417 | 24291 | 3121 |
| 56 | kha-báng | 20419 | 24293 | 3122 |
| 57 | kha-lá-óo-khe | 20420 | 24294 | 3123 |
| 59 | kha-tá-lok-guh | 20422 | 24296 | 3124 |
| 61 | khà-sàng | 20424 | 24298 | 3125 |
| 62 | khà-tsiàng | 20425 | 24299 | 3126 |
| 64 | kha̋ng-páng | 20427 | 24301 | 3127 |
| 65 | khe-tsiap-puh | 20428 | 24302 | 3128 |
| 66 | khi-móo-tsih | 20429 | 24303 | 3129 |
| 67 | khí-looh | 20430 | 24304 | 3130 |
| 68 | khiā-hang | 20431 | 24305 | 3131 |
| 69 | khit-teh | 20432 | 24306 | 3132 |
| 70 | khiű-khé | 20433 | 24307 | 3133 |
| 71 | khok-puh | 20434 | 24308 | 3134 |
| 72 | khōng-ku-lí | 20435 | 24309 | 3135 |
| 73 | khòng-buh | 20436 | 24310 | 3136 |
| 74 | khoo-lé-lah | 20437 | 24311 | 3137 |
| 75 | khoo-mí-sióng | 20438 | 24312 | 3138 |
| 76 | khòo-tòo | 20439 | 24313 | 3139 |
| 77 | khu-lá-tsih | 20440 | 24314 | 3140 |
| 78 | khu-lì-mù | 20441 | 24315 | 3141 |
| 79 | la-jí-ooh | 20442 | 24316 | 3142 |
| 80 | la-kiat-tooh | 20443 | 24317 | 3143 |
| 81 | la-mú-neh | 20444 | 24318 | 3144 |
| 82 | la̋i-jiòo-bù | 20445 | 24319 | 3145 |
| 83 | la̋i-lìn-gù | 20446 | 24320 | 3146 |
| 84 | lài-tah | 20447 | 24321 | 3147 |
| 85 | lê-bóng | 20448 | 24322 | 3148 |
| 86 | lè-sìr | 20449 | 24323 | 3149 |
| 87 | li-á-khah | 20450 | 24324 | 3150 |
| 88 | lia̋n-táng | 20451 | 24325 | 3151 |
| 89 | li̋n-jín | 20452 | 24326 | 3152 |
| 90 | lìn-gòo | 20453 | 24327 | 3153 |
| 91 | loo-lài-bà | 20454 | 24328 | 3154 |
| 92 | lòo-suh | 20455 | 24329 | 3155 |
| 93 | lóo-lí-á | 20456 | 24330 | 3156 |
| 94 | ma-lá-lí-á | 20457 | 24331 | 3157 |
| 95 | ma-lá-sóng | 20458 | 24332 | 3158 |
| 96 | ma-sà-tsì | 20459 | 24333 | 3159 |
| 97 | mài-kù | 20460 | 24334 | 3160 |
| 98 | me-lí-á | 20461 | 24335 | 3161 |
| 99 | me-lóng | 20462 | 24336 | 3162 |
| 100 | mè-sì | 20463 | 24337 | 3163 |
| 101 | mi-sín | 20464 | 24338 | 3164 |
| 103 | mòo-tà | 20466 | 24340 | 3165 |
| 104 | na̋i-lóng | 20467 | 24341 | 3166 |
| 105 | ne-kut-tái | 20468 | 24342 | 3167 |
| 106 | nè-tsiàng | 20469 | 24343 | 3168 |
| 107 | nőo-sín | 20470 | 24344 | 3169 |
| 108 | nóo-lih | 20471 | 24345 | 3170 |
| 109 | oo-bá-sáng | 20472 | 24346 | 3171 |
| 110 | oo-jí-sáng | 20473 | 24347 | 3172 |
| 111 | oo-lián | 20474 | 24348 | 3173 |
| 113 | oo-nè-sàng | 20476 | 24350 | 3174 |
| 115 | òo-bà | 20478 | 24352 | 3175 |
| 116 | pha-tsìn-kòo | 20479 | 24353 | 3176 |
| 117 | pha̋-siàn-tòo | 20480 | 24354 | 3177 |
| 119 | phàng-kù | 20482 | 24356 | 3178 |
| 120 | phi-á-nooh | 20483 | 24357 | 3179 |
| 121 | phiàn-tsih | 20484 | 24358 | 3180 |
| 122 | phi̋n-phóng | 20485 | 24359 | 3181 |
| 123 | phòng-phù | 20486 | 24360 | 3182 |
| 124 | phu-lóo-phé-lá | 20487 | 24361 | 3183 |
| 125 | pu-lù-sù | 20488 | 24362 | 3184 |
| 126 | sa-khá-lí-bah | 20489 | 24363 | 3185 |
| 127 | sa-khú-lah | 20490 | 24364 | 3186 |
| 129 | sa̋-bì-sù | 20492 | 24366 | 3187 |
| 130 | sài-sù | 20493 | 24367 | 3188 |
| 131 | sak-khuh | 20494 | 24368 | 3189 |
| 132 | sa̋m-phú-luh | 20495 | 24369 | 3190 |
| 133 | sàn-bah | 20496 | 24370 | 3191 |
| 135 | sè-hù | 20498 | 24372 | 3192 |
| 136 | si-á-geh | 20499 | 24373 | 3193 |
| 137 | sia-sín | 20500 | 24374 | 3194 |
| 140 | sio̍k-pháng | 20503 | 24377 | 3195 |
| 141 | si̍p-pán-ná | 20504 | 24378 | 3196 |
| 142 | sir-bé-lí-lái | 20505 | 24379 | 3197 |
| 143 | sir-tián-lè-sù | 20506 | 24380 | 3198 |
| 144 | sòo-sù | 20507 | 24381 | 3199 |
| 145 | su-khù-tà | 20508 | 24382 | 3200 |
| 146 | su-lit-pah | 20509 | 24383 | 3201 |
| 147 | su-tó-lip-puh | 20510 | 24384 | 3202 |
| 148 | sú-sih | 20511 | 24385 | 3203 |
| 149 | tha-khú-áng | 20512 | 24386 | 3204 |
| 150 | tha-khú-sih | 20513 | 24387 | 3205 |
| 151 | tha-thá-mih | 20514 | 24388 | 3206 |
| 152 | thài-ià | 20515 | 24389 | 3207 |
| 154 | thak-khooh | 20517 | 24391 | 3208 |
| 155 | thàn-gòo | 20518 | 24392 | 3209 |
| 157 | that-bí | 20520 | 24394 | 3210 |
| 158 | the-ní-suh | 20521 | 24395 | 3211 |
| 159 | thia̋n-pú-lah | 20522 | 24396 | 3212 |
| 160 | thoo-lá-khuh | 20523 | 24397 | 3213 |
| 161 | thoo-má-tooh | 20524 | 24398 | 3214 |
| 162 | tòo-sàng | 20525 | 24399 | 3215 |
| 163 | tshia̋n-pá-lah | 20526 | 24400 | 3216 |
| 164 | tsiok-kih | 20527 | 24401 | 3217 |
| 165 | tsioo-kóo-lè-tòo | 20528 | 24402 | 3218 |
| 166 | tsit-puh | 20529 | 24403 | 3219 |
| 167 | u-lóng | 20530 | 24404 | 3220 |
| 168 | ua-khá-móo-tooh | 20531 | 24405 | 3221 |
| 169 | ua-lù-tsuh | 20532 | 24406 | 3222 |
| 170 | ua-sá-bih | 20533 | 24407 | 3223 |
| 172 | ùn-tsiàng | 20535 | 24409 | 3224 |

## Validation

Both `python3 tools/lexicon.py validate` and `python3 tools/lexicon.py format --check` pass after synchronization: 3,224 entries, next ID 3,225. All 3,072 entries from the updated default workspace are unchanged.

## Synchronization with the updated default workspace

The default change `orppoulq` advanced to snapshot `2bf55ea8` and added 640 records, occupying IDs 2433–3072. Jujutsu rebased this import automatically and conflicted in the allocation counter. All 152 unpublished import entries were removed and re-added through the ordinary maintenance allocator as IDs 3073–3224; default entries and published IDs were preserved. The original-to-new ID and path mapping is retained in `.cache/moe-loanwords-import/id-reallocation.json`. The counter is 3225. The 20 identity decisions remain pending.
