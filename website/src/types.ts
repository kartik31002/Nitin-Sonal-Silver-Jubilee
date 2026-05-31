export interface PersonPhoto {
  thumbnail: string;
  driveUrl: string;
}

export interface Person {
  id: string;
  name: string;
  faceThumbnail: string;
  photoCount: number;
  photos: PersonPhoto[];
}

export interface PeoplePayload {
  eventTitle: string;
  generatedAt: string;
  people: Person[];
}
