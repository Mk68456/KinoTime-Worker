"""Inspect one film/episode, transferring no media to KinoTime."""
from tools.yougen_agent import matching_result
from tools.yougen_bridge import open_result, message_by_id, video_record, plain_label, BridgeError
from tools.yougen_worker import wait_card
from tools.yougen_discovery import menu, pages, next_page
from tools.provider_identity import full_video_title_matches, valid_voice_name


async def inspect_options(client, source, payload):
    results=await client.inline_query(source,payload['query'])
    title=matching_result(results,payload)
    index=next(i for i,r in enumerate(results) if r.title==title)
    last=await client.get_messages(source,limit=1)
    before=last[0].id if last else 0
    await open_result(client,source,payload['query'],index,title)
    card=await wait_card(client,source,before,payload)
    if not full_video_title_matches(video_record(card)['label'],payload['title']):
        raise BridgeError('Полное название видео не совпадает: варианты не показаны.')
    if payload['content_type']=='series':
        if (video_record(card)['season'],video_record(card)['episode']) != (payload['season'],payload['episode']):
            await menu(client,source,card.id,'Серии')
            await pages(client,source,card.id,r'Сезон [1-9][0-9]{0,2}',select=f"Сезон {payload['season']}")
            current=await message_by_id(client,source,card.id)
            if f"Сезон {payload['season']}" not in [plain_label(b.text) for r in current.buttons or [] for b in r]:
                raise BridgeError('Сезон не подтверждён.')
            await pages(client,source,card.id,r'[1-9][0-9]{0,2}',select=str(payload['episode']))
            card=await wait_card(client,source,before,payload,target_episode=True)
    await menu(client,source,card.id,'Озвучка')
    # Explicitly keep episode-specific availability, not all voices across a series.
    current=await message_by_id(client,source,card.id)
    labels=[plain_label(b.text) for r in current.buttons or [] for b in r]
    if 'Озвучки серии' in labels:
        await menu(client,source,card.id,'Озвучки серии')
    excluded={'Назад','Озвучка','Все озвучки','Озвучки серии','Вперед','Вперёд'}
    voices=[v for v in await pages(client,source,card.id,r'.+',max_pages=10)
            if valid_voice_name(v) and v not in excluded and not next_page(v) and any(c.isalnum() for c in v)]
    if not voices:
        raise BridgeError('Источник не показал доступных озвучек.')
    voice=payload.get('voice')
    if not voice:
        return voices
    if voice not in voices:
        raise BridgeError('Выбранная озвучка больше недоступна.')
    await menu(client,source,card.id,'Озвучка')
    await pages(client,source,card.id,r'.+',select=voice,max_pages=10)
    card=await wait_card(client,source,before,payload,voice=voice,target_episode=payload['content_type']=='series')
    if not full_video_title_matches(video_record(card)['label'],payload['title']):
        raise BridgeError('Полное название видео изменилось.')
    await menu(client,source,card.id,'Качество')
    return [q for q in await pages(client,source,card.id,r'[0-9]{3,4}p',max_pages=10)
            if q in {'240p','360p','480p','720p','1080p','1440p','2160p'}]
