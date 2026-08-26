export interface IUserFavorite {
    userId: string;
    menuId: number;
    displayOrder?: number;
    createdAt: Date;
    updatedAt: Date;
}