from datetime import datetime
from typing import Iterable
from drtapi import DRTApiException, DRTApi, Stop, Departure
from requests import RequestException

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, PreferencesEvent, PreferencesUpdateEvent, ItemEnterEvent
from ulauncher.api.shared.action import BaseAction
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction

class DRTExtension(Extension):
    def __init__(self):
        super(DRTExtension, self).__init__()
        self.drt = DRTApi()
        self.subscribe(PreferencesEvent, PreferencesListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateListener())
        self.subscribe(KeywordQueryEvent, KeywordQueryListener())

class PreferencesListener(EventListener):
    def on_event(self, ev: PreferencesEvent, ext: 'DRTExtension'):
        ext.drt.api_base = ev.preferences["drtapi"]

class PreferencesUpdateListener(EventListener):
    def on_event(self, ev: PreferencesUpdateEvent, ext: 'DRTExtension'):
        if ev.id == "drtapi":
            ext.drt.api_base = ev.new_value

class KeywordQueryListener(EventListener):
    def on_event(self, ev: KeywordQueryEvent, ext: 'DRTExtension'):
        try:
            if ev.get_argument() is None:
                return self.get_favorites(ev)
            elif ev.get_argument().startswith("departures "):
                return self.get_departures(ev, ext.drt, ev.get_argument().replace("departures ", "", 1))
            else:
                return self.get_stops(ev, ext.drt, ev.get_argument())
        except DRTApiException as ex:
            return RenderResultListAction([self.make_error(ex)])
        except RequestException as ex:
            return RenderResultListAction([self.make_error(ex)])

    # Actions

    def get_favorites(self, ev: KeywordQueryEvent) -> BaseAction:
        return RenderResultListAction([]) # TODO
    
    def get_stops(self, ev: KeywordQueryEvent, drt: DRTApi, arg: str) -> BaseAction:
        items = []
        for stop in drt.stops(ev.get_argument())[:5]:
            items.append(self.make_stop(ev.get_keyword(), stop))
        return RenderResultListAction(items)
    
    def get_departures(self, ev: KeywordQueryEvent, drt: DRTApi, arg: str) -> BaseAction:
        if arg.endswith(" refresh"):
            return SetUserQueryAction(ev.get_query().replace(" refresh", "", 1))

        items = []

        stop = drt.stop(arg)
        items.append(self.make_departures_stop(ev.get_keyword(), stop))

        for departure in drt.departures(stop.id)[:5]:
            items.append(self.make_departures_departure(departure))

        return RenderResultListAction(items)

    # Items

    def make_stop(self, kw: str, stop: Stop) -> ExtensionResultItem:
        return ExtensionResultItem(
            icon="images/icon.png",
            name=f"#{stop.id} {stop.name}",
            description=f"{stop.lat}, {stop.lon}",
            on_enter=SetUserQueryAction(f"{kw} departures {stop.id}")
        )
    
    def make_departures_stop(self, kw: str, stop: Stop) -> ExtensionResultItem:
        return ExtensionResultItem(
            icon="images/icon.png",
            name=f"{stop.name}",
            description=f"Last updated {datetime.now().strftime('%H:%M:%S')}",
            highlightable=False,
            on_enter=SetUserQueryAction(f"{kw} departures {stop.id} refresh")
        )
    
    def make_departures_departure(self, departure: Departure) -> ExtensionResultItem:
        desc = departure.time
        if not departure.is_real_time:
            desc += "*"
        if departure.time_late:
            desc += f" - {departure.time_late}"

        return ExtensionResultItem(
            icon="images/icon.png",
            name=f"{departure.route_id} {departure.destination}",
            description=desc,
            highlightable=False,
            on_enter=HideWindowAction()
        )

    def make_error(self, ex: Exception) -> ExtensionResultItem:
        return ExtensionResultItem(
            icon="images/icon.png",
            name=f"Error",
            description=str(ex),
            highlightable=False,
            on_enter=DoNothingAction()
        )

if __name__ == '__main__':
    DRTExtension().run()