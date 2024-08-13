class Orgao:
    
    def __init__(self, name: str, links: list[str], transparency_active: bool) -> None:
        self._name = name
        self._links = links
        self._transparency_active = transparency_active
        
    # def __init__(self, name: str, links: list[str]) -> None:
    #     self._name = name
    #     self._links = links
    
    def add_transparency_active(self, transparency_active: bool) -> None:
        self._transparency_active = transparency_active
        
    def add_link_cig(self, link_cig: str, last_updt: str = None) -> None:
        self._link_cig = link_cig
        self._cig_last_update = last_updt
        
    def add_link_portal(self, link_portal: str, last_updt: str = None) -> None:
        self._link_portal = link_portal
        self._portal_last_update = last_updt
        
    def add_portalPage_has_minutes(self, has_minutes: bool = False) -> None:
        self._portalPage_has_minutes = has_minutes
        
    def __repr__(self) -> str:
        if self._transparency_active:
            return f"Nome: {self._name}\nTransparência ativa: {self._transparency_active}\nLinks: {self._links}"
        else:
            return f"Nome: {self._name}\nTransparência ativa: {self._transparency_active}"