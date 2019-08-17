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
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction

class DRTExtension(Extension):
    def __init__(self):
        super(DRTExtension, self).__init__()
        self.drt = DRTApi()
        self.kw = "drt"
        self.subscribe(PreferencesEvent, PreferencesListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateListener())
        self.subscribe(KeywordQueryEvent, KeywordQueryListener())
        self.subscribe(ItemEnterEvent, ItemEnterListener())

    # Storage
    fav = []
    def fav_get(self) -> Iterable[Stop]:
        return DRTExtension.fav
    
    def fav_set(self, stops: Iterable[Stop]):
        DRTExtension.fav = stops

    def fav_add(self, id: str):
        stop = self.drt.stop(str(id))
        self.fav_remove(str(id))
        self.fav_set([stop] + list(self.fav_get()))
    
    def fav_remove(self, id: str):
        self.fav_set(list(filter(lambda x: str(x.id) != str(id), self.fav_get())))
    
    def fav_has(self, id: str) -> bool:
        return any([str(stop.id) == str(id) for stop in self.fav_get()])

    # Actions

    def get_favorites(self) -> BaseAction:
        return RenderResultListAction([self.make_stop(stop) for stop in self.fav_get()]) # TODO
    
    def get_stops(self, ev: KeywordQueryEvent, arg: str) -> BaseAction:
        items = []
        for stop in self.drt.stops(ev.get_argument())[:5]:
            items.append(self.make_stop(stop))
        return RenderResultListAction(items)
    
    def get_departures(self, ev: KeywordQueryEvent, arg: str) -> BaseAction:
        if arg.endswith(" refresh"):
            return SetUserQueryAction(ev.get_query().replace(" refresh", "", 1))

        items = []

        stop = self.drt.stop(arg)
        items.append(self.make_departures_stop(stop))

        for departure in self.drt.departures(stop.id)[:5]:
            items.append(self.make_departures_departure(departure))

        return RenderResultListAction(items)

    # Items

    def make_stop_menu(self, stop: Stop) -> BaseAction:
        back = ExtensionResultItem(
            icon="images/icon.png",
            name="Back",
            highlightable=False,
            on_enter=SetUserQueryAction(f"{self.kw} {stop.id}")
        )
        if self.fav_has(stop.id):
            return RenderResultListAction([
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="Remove from favorites",
                    highlightable=False,
                    on_enter=ExtensionCustomAction(f"remove {stop.id}")
                ),
                back
            ])
        else:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="Add to favorites",
                    highlightable=False,
                    on_enter=ExtensionCustomAction(f"add {stop.id}")
                ),
                back
            ])

    def make_stop(self, stop: Stop) -> ExtensionResultItem:
        return ExtensionResultItem(
            icon="images/icon.png",
            name=f"#{stop.id} {stop.name}",
            description=f"{stop.lat}, {stop.lon}",
            on_enter=SetUserQueryAction(f"{self.kw} departures {stop.id}"),
            on_alt_enter=self.make_stop_menu(stop)
        )

    def make_departures_stop(self, stop: Stop) -> ExtensionResultItem:
        return ExtensionResultItem(
            icon="images/icon.png",
            name=f"{stop.name}",
            description=f"Last updated {datetime.now().strftime('%H:%M:%S')}",
            highlightable=False,
            on_enter=SetUserQueryAction(f"{self.kw} departures {stop.id} refresh"),
            on_alt_enter=self.make_stop_menu(stop)
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

class PreferencesListener(EventListener):
    def on_event(self, ev: PreferencesEvent, ext: DRTExtension):
        ext.kw = ev.preferences["kw"]
        ext.drt.api_base = ev.preferences["drtapi"]

class PreferencesUpdateListener(EventListener):
    def on_event(self, ev: PreferencesUpdateEvent, ext: DRTExtension):
        if ev.id == "kw":
            ext.kw = ev.new_value
        elif ev.id == "drtapi":
            ext.drt.api_base = ev.new_value

class KeywordQueryListener(EventListener):
    def on_event(self, ev: KeywordQueryEvent, ext: DRTExtension) -> BaseAction:
        try:
            if ev.get_argument() is None:
                return ext.get_favorites()
            elif ev.get_argument().startswith("departures "):
                return ext.get_departures(ev, ev.get_argument().replace("departures ", "", 1))
            else:
                return ext.get_stops(ev, ev.get_argument())
        except DRTApiException as ex:
            return RenderResultListAction([self.make_error(ex)])
        except RequestException as ex:
            return RenderResultListAction([self.make_error(ex)])


class ItemEnterListener(EventListener):
    def on_event(self, ev: ItemEnterEvent, ext: DRTExtension) -> BaseAction:
        if ev.get_data().startswith("add "):
            ext.fav_add(ev.get_data().replace("add ", "", 1))
            return SetUserQueryAction(f"{ext.kw} ")
        elif ev.get_data().startswith("remove "):
            ext.fav_remove(ev.get_data().replace("remove ", "", 1))
            return SetUserQueryAction(f"{ext.kw} ")
        else:
            return DoNothingAction()

if __name__ == '__main__':
    DRTExtension().run()